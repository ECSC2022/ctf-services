package main

import (
	"cantina/client/connector"
	"cantina/common/can"
	"cantina/gateway/proxy"
	"fmt"
	"os"
)

func main() {

	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "Please provide a gw server address")
		return
	}

	addr := os.Args[1]

	canProx := connector.NewConnector(
		addr,
	)

	canmsg := can.Message{
		ArbitrationId: 999,
		Data:          []byte("testingAAAAAAAAAAAA\x00"),
	}

	msg, _ := proxy.NewProxyMessageCanFrame(&canmsg)

	canProx.SendQueue() <- &msg

	for {
		val := <-canProx.RecvQueue()

		// TODO add error message type
		switch val.Type {
		case proxy.CanFrame:
			canmsg := new(can.Message)
			canmsg.Unmarshal(val.Data)
			fmt.Println(canmsg)
		}

		fmt.Println(val)
	}

}
