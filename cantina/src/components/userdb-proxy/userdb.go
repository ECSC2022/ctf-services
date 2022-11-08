package main

import (
	"cantina/common/can"
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/components"
	"cantina/common/kex"
	"cantina/user-db/proxy"
	"cantina/user-db/udb"

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
	env := new(udb.Env)

	// Set up logging facilities
	env.Log = log.New(os.Stderr, "[UDB] ", log.Ldate|log.Ltime)

	// Parsing env vars
	canInterface := "vcan0"
	if val, ok := os.LookupEnv("CAN_IF"); ok {
		canInterface = val
	}
	env.DataDir = "/data"
	if val, ok := os.LookupEnv("DATA_DIR"); ok {
		env.DataDir = val
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
	env.Log.Printf(
		"Connected to '%s'\n",
		canInterface,
	)

	defer bus.Shutdown()
	env.Log.Printf(
		"Waiting for keyserver",
	)

	// Initialize cipher
	env.SymmCipher = &cipher.Cipher{}

	// Initialize key exchange
	env.KeyExchange, err = kex.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		kex.ClientIds{
			RecvPubkey:    udb.MSGID_KEY_EXCH_PUBKEY_BROADCAST,
			RecvSymmetric: udb.MSGID_KEY_EXCH_SHARE_SYMMETRIC,
			RecvRekey:     udb.MSGID_KEY_EXCH_REKEY_NOTIFY,
			Request:       udb.MSGID_KEY_EXCH_REQ_USER_DB,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize key exchange.\n")
		return
	}

	// Initialize canopy server
	env.JukeboxRequest, err = canopy.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start:      udb.MSGID_USER_DB_JUKEBOX_START,
			Data:       udb.MSGID_USER_DB_JUKEBOX_DATA,
			ReplyStart: udb.MSGID_USER_DB_JUKEBOX_REPLY_START,
			ReplyData:  udb.MSGID_USER_DB_JUKEBOX_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf(
			"Can't initialize JukeboxRequest: %v\n",
			err,
		)
		return
	}

	// Set reply builder
	jukeboxReply, _ := proxy.NewProxyReplyBuilder(env, true)
	env.JukeboxReplyBuilder = jukeboxReply
	env.JukeboxRequest.SetReplyBuilder(jukeboxReply)

	// Initialize canopy client for user requests pickup
	env.UserRequest, err = canopy.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start:      udb.MSGID_USER_DB_USERREQ_START,
			Data:       udb.MSGID_USER_DB_USERREQ_DATA,
			ReplyStart: udb.MSGID_USER_DB_USERREQ_REPLY_START,
			ReplyData:  udb.MSGID_USER_DB_USERREQ_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf(
			"Can't initialize order pickup: %v.\n",
			err,
		)
		return
	}

	// Set reply builder
	userRequestReply, err := proxy.NewProxyReplyBuilder(env, false)
	userRequestReply.Remoteaccess = true
	env.UserRequestBuilder = userRequestReply
	env.UserRequest.SetReplyBuilder(userRequestReply)

	// Set session initializer
	env.UserRequestSession, err = proxy.NewProxySessionInitializer(
		env)
	env.UserRequest.SetSessionInitializer(env.UserRequestSession)

	// Collect receive handlers
	recvHandlers := make(map[uint32]components.RecvHandler)
	maps.Copy(recvHandlers, env.KeyExchange.RecvHandlers())
	maps.Copy(recvHandlers, env.JukeboxRequest.RecvHandlers())
	maps.Copy(recvHandlers, env.UserRequest.RecvHandlers())

	// Run component update tasks
	go env.KeyExchange.UpdateLoop()
	go env.JukeboxRequest.UpdateLoop()
	go env.UserRequest.UpdateLoop()

	// Defer cleanup
	defer env.JukeboxRequest.Shutdown()
	defer env.UserRequest.Shutdown()
	defer env.KeyExchange.Shutdown()

	// Set up CAN filters
	var canFilters []unix.CanFilter
	canFilters = append(canFilters, unix.CanFilter{
		Id:   0x100,
		Mask: 0x1fffffec,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id:   udb.MSGID_USER_DB_JUKEBOX_START,
		Mask: 0x1ffffffc,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id:   udb.MSGID_USER_DB_USERREQ_START,
		Mask: 0x1ffffffc,
	})
	if err = bus.SetFilters(&canFilters); err != nil {
		log.Fatalln("Can't set CAN filters")
	}

	// Run message handling loop
	for msg := range bus.RecvQueue() {
		handler, ok := recvHandlers[msg.ArbitrationId]
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
