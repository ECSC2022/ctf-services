package main

import (
	"cantina/common/can"
	"cantina/common/tickets"
	"cantina/gateway/proxy"
	"context"
	"flag"
	"log"
	"os"
	"strconv"
	"time"

	"golang.org/x/sys/unix"
)

var localAddr *string = flag.String("l", "0.0.0.0:10020", "local address")
var remoteAddr *string = flag.String("r", "localhost:7777", "remote address")
var canIf *string = flag.String("i", "vcan0", "can interface")

var server_pubkey = make([]byte, 32)

func wait_for_key(log *log.Logger) {
	msgid_pubkey_request := 0x103
	val, ok := os.LookupEnv("MSGID_KEY_EXCH_REQUEST_PUBKEY")
	if ok {
		conv, err := strconv.Atoi(val)
		if err != nil {
			log.Println("wrong MSGID_KEY_EXCH_REQUEST_PUBKEY format")
			panic(err)
		}
		msgid_pubkey_request = conv
	}

	msgid_pubkey_broadcast := 0x100
	val, ok = os.LookupEnv("MSGID_KEY_EXCH_PUBKEY_BROADCAST")
	if ok {
		conv, err := strconv.Atoi(val)
		if err != nil {
			log.Println("wrong MSGID_KEY_EXCH_PUBKEY_BROADCAST format")
			panic(err)
		}
		msgid_pubkey_request = conv
	}

	filt_list := []unix.CanFilter{
		unix.CanFilter{
			Id:   uint32(msgid_pubkey_broadcast),
			Mask: unix.CAN_EFF_MASK,
		},
	}

	// Let's do this until we have a key
	for {
		bus, err := can.NewBus(*canIf)
		if err != nil {
			log.Printf(
				"Can't connect to '%s': %v",
				*canIf,
				err,
			)
		} else {

			err = bus.SetFilters(&filt_list)
			if err != nil {
				panic(err)
			}
			log.Println("Sending key request")
			bus.SendQueue() <- &can.Message{
				ArbitrationId: uint32(msgid_pubkey_request),
				Data:          []byte{},
			}

			log.Println("Waiting for key message")
			msg := <-bus.RecvQueue()
			copy(server_pubkey, msg.Data[32:])
			log.Println("Key message received")
			bus.Shutdown()
			break
		}
		// Wait and try again
		time.Sleep(1 * time.Second)
		continue

	}
}

func main() {

	// Set up logging facilities
	log := log.New(os.Stderr, "[GW] ", log.Ldate|log.Ltime)

	flag.Parse()
	log.Printf("Proxy: %v <--> %v", *localAddr, *canIf)

	wait_for_key(log)

	log.Println("Start listening for connections")

	ctx := context.Background()

	tm := tickets.NewManager()
	tm.SetPublicKey(server_pubkey)

	canProxy, _ := proxy.NewCanProxy(*canIf, *localAddr, log, tm)
	canProxy.Start(ctx)

}
