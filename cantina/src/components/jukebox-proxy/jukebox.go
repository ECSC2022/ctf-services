package main

import (
	"cantina/common/can"
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/components"
	"cantina/common/kex"
	"cantina/common/tickets"
	"cantina/jukebox/jukebox"
	"cantina/jukebox/remoteaccess"
	"cantina/jukebox/routes"
	"cantina/jukebox/streamer"
	jtickets "cantina/jukebox/tickets"

	"log"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/maps"
	"golang.org/x/sys/unix"
)

func main() {
	var err error
	var bus *can.Bus

	// Create storage for request environment
	env := new(jukebox.Env)

	// Set up logging facilities
	env.Log = log.New(os.Stderr, "[JKBOX] ", log.Ldate|log.Ltime)

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

	env.Log.Println(remoteaccess.Info())

	// Initialize ticket verification endpoint
	env.TicketManager = tickets.NewManager()
	env.UserTicketManager = jtickets.NewManager()

	// Initialize cipher
	env.SymmCipher = &cipher.Cipher{}

	// Initialize key exchange
	env.KeyExchange, err = kex.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		kex.ClientIds{
			RecvPubkey:    jukebox.MSGID_KEY_EXCH_PUBKEY_BROADCAST,
			RecvSymmetric: jukebox.MSGID_KEY_EXCH_SHARE_SYMMETRIC,
			RecvRekey:     jukebox.MSGID_KEY_EXCH_REKEY_NOTIFY,
			Request:       jukebox.MSGID_KEY_EXCH_REQ_JUKEBOX,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize key exchange.\n")
		return
	}

	// Initialize canopy client
	env.UserDbRequest, err = canopy.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start:      jukebox.MSGID_USER_DB_JUKEBOX_START,
			Data:       jukebox.MSGID_USER_DB_JUKEBOX_DATA,
			ReplyStart: jukebox.MSGID_USER_DB_JUKEBOX_REPLY_START,
			ReplyData:  jukebox.MSGID_USER_DB_JUKEBOX_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize canopy client.\n")
		return
	}

	// Initialize user cipher
	usercipher := &cipher.Cipher{}
	usercipher.Update(make([]byte, 32))

	// Initialize canopy server for user requests
	env.UserRequest, err = canopy.NewServer(
		usercipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start:      jukebox.MSGID_JUKEBOX_USERREQ_START,
			Data:       jukebox.MSGID_JUKEBOX_USERREQ_DATA,
			ReplyStart: jukebox.MSGID_JUKEBOX_USERREQ_REPLY_START,
			ReplyData:  jukebox.MSGID_JUKEBOX_USERREQ_REPLY_DATA,
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
	userRequestReply := &remoteaccess.RemoteAccessReplyBuilder{env}
	env.UserRequestBuilder = userRequestReply
	env.UserRequest.SetReplyBuilder(userRequestReply)

	recvHandlers := make(map[uint32]components.RecvHandler)
	maps.Copy(recvHandlers, env.KeyExchange.RecvHandlers())
	maps.Copy(recvHandlers, env.UserDbRequest.RecvHandlers())
	maps.Copy(recvHandlers, env.UserRequest.RecvHandlers())

	env.Streamer = streamer.NewStreamer(env.Log,
		bus.SendQueue())

	// Run component update tasks
	//go env.JukeboxRequest.UpdateLoop()
	//go env.UserRequest.UpdateLoop()
	go env.KeyExchange.UpdateLoop()
	go env.Streamer.HandleStreaming()

	router := gin.Default()
	rc := &routes.RouterContext{Env: env}
	router.POST("/proxy", rc.NewProxy)
	router.POST("/ticket/validate", rc.NewTicket)
	go router.Run(":10025")

	// Defer cleanup
	defer env.JukeboxRequest.Shutdown()
	//	defer env.UserRequest.Shutdown()
	defer env.KeyExchange.Shutdown()

	// Set up CAN filters
	var canFilters []unix.CanFilter
	canFilters = append(canFilters, unix.CanFilter{
		Id:   0x100,
		Mask: 0x1fffffec,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id:   jukebox.MSGID_USER_DB_JUKEBOX_REPLY_START,
		Mask: 0x1ffffffc,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id:   jukebox.MSGID_JUKEBOX_USERREQ_START,
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
