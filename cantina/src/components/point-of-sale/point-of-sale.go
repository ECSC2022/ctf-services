package main

import (
	"cantina/common/can"
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/components"
	"cantina/common/kex"
	"cantina/common/tickets"
	"cantina/point-of-sale/pos"
	"cantina/point-of-sale/routes"
	"encoding/base64"
	"encoding/binary"

	"crypto/rand"
	"log"
	"os"
	"time"
	"mime"

	"github.com/gin-contrib/sessions"
	gormsessions "github.com/gin-contrib/sessions/gorm"
	"github.com/gin-contrib/static"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"golang.org/x/exp/maps"
	"golang.org/x/sys/unix"
)

func main() {
	var err error
	var bus *can.Bus

	// Create storage for request environment
	env := new(pos.Env)

	// Set up logging facilities
	env.Log = log.New(os.Stderr, "[POS] ", log.Ldate|log.Ltime)

	// Parsing env vars
	canInterface := "vcan0"
	if val, ok := os.LookupEnv("CAN_IF"); ok {
		canInterface = val
	}
	staticDir := "/static"
	if val, ok := os.LookupEnv("STATIC_DIR"); ok {
		staticDir = val
	}

	// Get gamebot public key for PoW
	if val, ok := os.LookupEnv("GAMEBOT_PUBKEY"); ok {
		env.GamebotPubKey, err =
			base64.StdEncoding.DecodeString(val)
		if err != nil {
			env.Log.Fatalf(
				"Invalid gamebot pubkey: %v",
				err,
			)
		}
	} else {
		env.Log.Fatalln("No GAMEBOT_PUBKEY provided.")
	}

	// Load the order items
	env.OrderItems, err = pos.LoadItems()
	if err != nil {
		env.Log.Fatalf("Couldn't parse order items: %v", err)
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

	// Initialize ticket verification endpoint
	env.TicketManager = tickets.NewManager()

	// Initialize cipher
	env.SymmCipher = &cipher.Cipher{}

	// Initialize some entropy
	dataBytes := [32]byte{}
	data := []uint32{
		3395412008,
		942752005,
		1307775173,
		2114792933,
		2212373885,
		99049143,
		2471157402,
		1123941560,
	}
	for i, number := range data {
		binary.LittleEndian.PutUint32(
			dataBytes[i*4:(i+1)*4],
			number,
		)
	}

	// Initialize key exchange
	env.KeyExchange, err = kex.NewClientDetached(
		env.SymmCipher,
		bus.SendQueue(),
		dataBytes,
		kex.ClientIds{
			RecvPubkey:
				pos.MSGID_KEY_EXCH_PUBKEY_BROADCAST,
			RecvSymmetric:
				pos.MSGID_KEY_EXCH_SHARE_SYMMETRIC,
			RecvRekey:
				pos.MSGID_KEY_EXCH_REKEY_NOTIFY,
			Request:
				pos.MSGID_KEY_EXCH_REQ_POS,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize key exchange.\n")
		return
	}

	// Initialize canopy client
	env.OrderCreation, err = canopy.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start: pos.MSGID_POS_ORDER_START,
			Data: pos.MSGID_POS_ORDER_DATA,
			ReplyStart: pos.MSGID_POS_ORDER_REPLY_START,
			ReplyData: pos.MSGID_POS_ORDER_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize canopy client.\n")
		return
	}

	// Initialize canopy client for ticketing
	env.TicketCreation, err = canopy.NewClient(
		env.SymmCipher,
		bus.SendQueue(),
		canopy.MessageIds{
			Start: pos.MSGID_POS_TICKET_START,
			Data: pos.MSGID_POS_TICKET_DATA,
			ReplyStart: pos.MSGID_KEY_TICKET_REPLY_START,
			ReplyData: pos.MSGID_KEY_TICKET_REPLY_DATA,
		},
		env.Log,
	)
	if err != nil {
		env.Log.Printf("Can't initialize ticketing client.\n")
		return
	}

	// Collect receive handlers
	recvHandlers := make(map[uint32]components.RecvHandler)
	maps.Copy(recvHandlers, env.KeyExchange.RecvHandlers())
	maps.Copy(recvHandlers, env.OrderCreation.RecvHandlers())
	maps.Copy(recvHandlers, env.TicketCreation.RecvHandlers())

	// Get random values for cookie keys
	// https://pkg.go.dev/github.com/gin-contrib/sessions/cookie
	cookieAuthKey := make([]byte, 64)
	_, err = rand.Read(cookieAuthKey)
	if err != nil {
		env.Log.Printf("Can't get random reads: %v", err);
		return
	}
	cookieEncKey := make([]byte, 32)
	_, err = rand.Read(cookieEncKey)
	if err != nil {
		env.Log.Printf("Can't get random reads: %v", err);
		return
	}

	// Initialize web framework and session storage
	router := gin.Default()
	sessionDb, err := gorm.Open(
		sqlite.Open("file::memory:?cache=shared"),
		&gorm.Config{},
	)
	if err != nil {
		env.Log.Printf(
			"Can't initialize in-memory DB for " +
			"session storage: %v",
			err,
		)
		return
	}
	sessionStore := gormsessions.NewStore(
		sessionDb,
		true,
		cookieAuthKey,
		cookieEncKey,
	)
	router.Use(sessions.Sessions("pos-sessions", sessionStore))

        // Add API routes
        rc := &routes.RouterContext{ Env: env }
	router.Use(
		static.Serve("/", static.LocalFile(staticDir, false)),
	)
	mime.AddExtensionType(".js", "application/javascript")
	router.NoRoute(func(c *gin.Context) {
		c.File(staticDir + "/index.html")
	})
        router.POST("/create_pow", rc.CreatePow)
        router.POST("/ticket", rc.CreateTicket)
        router.GET("/items", rc.GetMenuItems)
        router.POST("/order", rc.NewOrder)

	// Run component update tasks
	go router.Run()
	go env.KeyExchange.UpdateLoop()


	// Set up CAN filters
	var canFilters []unix.CanFilter
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x100,
		Mask: 0x1fffffec,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x200,
		Mask: 0x1ffffffc,
	})
	canFilters = append(canFilters, unix.CanFilter{
		Id: 0x210,
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
