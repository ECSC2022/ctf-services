package main

import (
	"cantina/common/can"
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/components"
	"cantina/common/kex"
	"cantina/order-db/odb"
	"cantina/order-db/storage"
	"os/exec"
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
	env := new(odb.Env)

	// Set up logging facilities
	env.Log = log.New(os.Stderr, "[ODB] ", log.Ldate|log.Ltime)

	// Parsing env vars
	canInterface := "vcan0"
	if val, ok := os.LookupEnv("CAN_IF"); ok {
		canInterface = val
	}
	env.DataDir = "/data"
	if val, ok := os.LookupEnv("DATA_DIR"); ok {
		env.DataDir = val
	}

	// Load most recent order from file
	recentOrderId := 0
	orderIdPath := filepath.Join(env.DataDir, "order_id")
	orderIdData, err := os.ReadFile(orderIdPath)
	if err == nil {
		v, err := strconv.Atoi(string(orderIdData))
		if err == nil {
			recentOrderId = v
		}
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
	env.KeyExchange, err = kex.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		kex.ClientIds{
			RecvPubkey:
				odb.MSGID_KEY_EXCH_PUBKEY_BROADCAST,
			RecvSymmetric:
				odb.MSGID_KEY_EXCH_SHARE_SYMMETRIC,
			RecvRekey:
				odb.MSGID_KEY_EXCH_REKEY_NOTIFY,
			Request:
				odb.MSGID_KEY_EXCH_REQ_ORDER_DB,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize key exchange.\n")
		return
	}

	// Initialize canopy client
	env.OrderCreation, err = canopy.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start: odb.MSGID_POS_ORDER_START,
			Data: odb.MSGID_POS_ORDER_DATA,
			ReplyStart: odb.MSGID_POS_ORDER_REPLY_START,
			ReplyData: odb.MSGID_POS_ORDER_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf(
			"Can't initialize OrderCreation: %v\n",
			err,
		)
		return
	}

	// Set reply builder
	orderCreationReply := &storage.CreationReplyBuilder{ Env: env }
	orderCreationReply.OrderId = uint32(recentOrderId)
	env.OrderCreationBuilder = orderCreationReply
	env.OrderCreation.SetReplyBuilder(orderCreationReply)

	// Initialize canopy client for order pickup
	env.OrderPickup, err = canopy.NewServer(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start: odb.MSGID_CLIENT_OPICKUP_START,
			Data: odb.MSGID_CLIENT_OPICKUP_DATA,
			ReplyStart: odb.MSGID_ODB_OPICKUP_REPLY_START,
			ReplyData: odb.MSGID_ODB_OPICKUP_REPLY_DATA,
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
	orderPickupReply := &storage.PickupReplyBuilder{ Env: env }
	env.OrderPickupBuilder = orderPickupReply
	env.OrderPickup.SetReplyBuilder(orderPickupReply)

	// Set session initializer
	env.OrderPickupSession = &storage.PickupSessionInitializer{
		Env: env,
	}
	env.OrderPickup.SetSessionInitializer(env.OrderPickupSession)

	// Collect receive handlers
	recvHandlers := make(map[uint32]components.RecvHandler)
	maps.Copy(recvHandlers, env.KeyExchange.RecvHandlers())
	maps.Copy(recvHandlers, env.OrderCreation.RecvHandlers())
	maps.Copy(recvHandlers, env.OrderPickup.RecvHandlers())

	// Run component update tasks
	go env.KeyExchange.UpdateLoop()
	go env.OrderCreation.UpdateLoop()
	go env.OrderPickup.UpdateLoop()

	// Cleanup loop
	go func() {
		for {
			env.Log.Printf("Cleanup command exeuction")
			cmd := exec.Command("/usr/bin/find",
				env.DataDir,
				"-mmin", "+30",
				"-delete",
			)
			err := cmd.Run()
			if err != nil {
				env.Log.Printf("Error during cleanup");
			}

			time.Sleep(20 * time.Second);
		}
	}()

	// Defer cleanup
	defer env.OrderCreation.Shutdown()
	defer env.OrderPickup.Shutdown()
	defer env.KeyExchange.Shutdown()

	// Set up CAN filters
	var canFilters []unix.CanFilter
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x100,
		Mask: 0x1fffffc0,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x200,
		Mask: 0x1ffffffc,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x2000,
		Mask: 0x1ffffffe,
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
