package main

import (
	"cantina/common/can"
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/components"
	"cantina/common/kex"
	"cantina/keyserver/ks"
	"cantina/keyserver/tickets"
	"path/filepath"
	"strconv"

	"log"
	"os"
	"time"

	"golang.org/x/exp/maps"
	"golang.org/x/sys/unix"
)

func main() {
	var err error
	var bus *can.Bus

	// Create storage for request environment
	env := new(ks.Env)

	// Set up logging facilities
	env.Log = log.New(os.Stderr, "[KSV] ", log.Ldate|log.Ltime)

	// Parsing env vars
	canInterface := "vcan0"
	if val, ok := os.LookupEnv("CAN_IF"); ok {
		canInterface = val
	}
	env.DataDir = "/data"
	if val, ok := os.LookupEnv("DATA_DIR"); ok {
		env.DataDir = val
	}
	rekeyInterval := 75 * time.Second
	if val, ok := os.LookupEnv("REKEY_INTERVAL"); ok {
		v, err := strconv.Atoi(val)
		if err != nil {
			rekeyInterval = time.Duration(v) * time.Second
		}
	}

	// Try to read private keys from file
	var storedPrivateKey, storedSigningKey []byte
	key, err := os.ReadFile(
		filepath.Join(env.DataDir, "private.key"),
	)
	if err == nil {
		storedPrivateKey = make([]byte, len(key))
		copy(storedPrivateKey, key)
	}
	key, err = os.ReadFile(
		filepath.Join(env.DataDir, "signing.key"),
	)
	if err == nil {
		storedSigningKey = make([]byte, len(key))
		copy(storedSigningKey, key)
	}

	// We try connecting to a bus until it works
	for {
		env.Log.Printf(
			"Trying to connect to '%s'\n",
			canInterface,
		)

		bus, err = can.NewBus(canInterface)
		if err == nil {
			break
		}

		env.Log.Printf(
			"Can't connect to '%s': %v",
			canInterface,
			err,
		)

		// Wait and try again
		time.Sleep(1 * time.Second)
		continue
	}

	// Shutdown bus when returning from main
	defer bus.Shutdown()

	// Initialize cipher
	env.SymmCipher = &cipher.Cipher{}

	// Initialize key exchange
	env.KeyExchange, err = kex.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		kex.ServerIds{
			PubkeyBroadcast: ks.MSGID_KEY_EXCH_PUBKEY_BROADCAST,
			ShareSymmetric:  ks.MSGID_KEY_EXCH_SHARE_SYMMETRIC,
			RekeyNotify:     ks.MSGID_KEY_EXCH_REKEY_NOTIFY,
			Request:         ks.MSGID_KEY_EXCH_REQUEST_PUBKEY,
			SymmetricReq: map[uint32]string{
				ks.MSGID_KEY_EXCH_REQ_ORDER_DB: "Order-DB key exchange",
				ks.MSGID_KEY_EXCH_REQ_POS:      "Point-of-sale key exchange",
				ks.MSGID_KEY_EXCH_REQ_USER_DB:  "User-DB key exchange",
				ks.MSGID_KEY_EXCH_REQ_JUKEBOX:  "Jukebox key exchange",
			},
			RekeyReq: map[uint32]string{
				ks.MSGID_KEY_EXCH_SYMM_ORDER_DB_REKEY: "Order-DB rekey",
				ks.MSGID_KEY_EXCH_SYMM_POS_REKEY:      "Point-of-sale rekey",
				ks.MSGID_KEY_EXCH_SYMM_USER_DB_REKEY:  "User-DB rekey",
				ks.MSGID_KEY_EXCH_SYMM_JUKEBOX_REKEY:  "Jukebox rekey",
			},
		},
		storedPrivateKey,
		storedSigningKey,
		rekeyInterval,
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize key exchange.\n")
		return
	}

	// TODO: Store keys on file
	if storedPrivateKey == nil {
		env.Log.Println("Saving generated private key.")
		err = os.WriteFile(
			filepath.Join(env.DataDir, "private.key"),
			env.KeyExchange.PrivateKey[:],
			0600,
		)
		if err != nil {
			env.Log.Printf("Couldn't save key: %v", err)
		}
	}
	if storedSigningKey == nil {
		env.Log.Println("Saving generated signing key.")
		err = os.WriteFile(
			filepath.Join(env.DataDir, "signing.key"),
			env.KeyExchange.SigningKey[:],
			0600,
		)
		if err != nil {
			env.Log.Printf("Couldn't save key: %v", err)
		}
	}

	// Initialize ticket creation
	env.TicketCreation, err = canopy.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start:      ks.MSGID_POS_TICKET_START,
			Data:       ks.MSGID_POS_TICKET_DATA,
			ReplyStart: ks.MSGID_KEY_TICKET_REPLY_START,
			ReplyData:  ks.MSGID_KEY_TICKET_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf(
			"Can't initialize TicketCreation: %v\n",
			err,
		)
		return
	}

	// Set reply builder
	ticketCreationReply := &tickets.TicketReplyBuilder{Env: env}
	env.TicketReplyBuilder = ticketCreationReply
	env.TicketCreation.SetReplyBuilder(ticketCreationReply)

	// Collect receive handlers
	recvHandlers := make(map[uint32]components.RecvHandler)
	maps.Copy(recvHandlers, env.KeyExchange.RecvHandlers())
	maps.Copy(recvHandlers, env.TicketCreation.RecvHandlers())

	// Run component update tasks
	go env.KeyExchange.UpdateLoop()
	go env.TicketCreation.UpdateLoop()

	// Defer cleanup
	defer env.TicketCreation.Shutdown()
	defer env.KeyExchange.Shutdown()

	// Set up CAN filters
	var canFilters []unix.CanFilter
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x100,
		Mask: 0x1fc,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x100,
		Mask: 0x1ce,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x300,
		Mask: 0x3ce,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x210,
		Mask: 0x3fc,
	})
	if err = bus.SetFilters(&canFilters); err != nil {
		log.Fatalln("Can't set CAN filters")
	}

	// Run message handling loop
	for msg := range bus.RecvQueue() {
		mid := uint16(msg.ArbitrationId)
		handler, ok := recvHandlers[uint32(mid)]
		if !ok {
			continue
		}

		err := handler(msg)
		if err == nil {
			continue
		}

		env.Log.Printf("Error handling message: %v", err)
	}
}
