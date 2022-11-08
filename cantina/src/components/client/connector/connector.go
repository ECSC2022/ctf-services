package connector

import (
	"cantina/gateway/proxy"
	"fmt"
	"io"
	"log"
	"net"
	"sync"

	"github.com/vmihailenco/msgpack"
	"golang.org/x/sys/unix"
)

type Connector struct {
	host      string
	sendQueue chan *proxy.ProxyMessage
	stopSend  chan interface{}
	recvQueue chan *proxy.ProxyMessage
	running   bool
	wait      *sync.WaitGroup
	conn      *net.TCPConn
}

func NewConnector(
	host string,
) (c *Connector) {

	tcpAddr, err := net.ResolveTCPAddr("tcp", host)
	if err != nil {
		println("ResolveTCPAddr failed:", err.Error())
		return
	}
	conn, err := net.DialTCP("tcp", nil, tcpAddr)
	if err != nil {
		println("Dial failed:", err.Error())
		return
	}

	c = &Connector{
		host:      host,
		sendQueue: make(chan *proxy.ProxyMessage),
		stopSend:  make(chan interface{}),
		running:   true,
		recvQueue: make(chan *proxy.ProxyMessage),
		wait:      &sync.WaitGroup{},
		conn:      conn,
	}

	c.wait.Add(2)
	// Start receiving and sending loops
	go c.recvLoop()
	go c.sendLoop()

	return
}

func (c *Connector) Shutdown() {
	go func() {
		c.running = false
		c.stopSend <- nil
		close(c.recvQueue)
		close(c.stopSend)
		c.wait.Wait()
		c.conn.Close()
	}()
}

func (c *Connector) ResetFilters() (err error) {
	//	allow := unix.CanFilter{
	//		Id:   0x20000000,
	//		Mask: 0x1FFFF800,
	//	}
	// TODO send to gateway
	return
}

func (c *Connector) SetFilters(filters *[]unix.CanFilter) (err error) {

	//	// Enable CAN-FD frames
	//	err = unix.SetsockoptCanRawFilter(
	//		int(b.file.Fd()),
	//		unix.SOL_CAN_RAW,
	//		unix.CAN_RAW_FILTER,
	//		*filters,
	//	)
	//	if err != nil {
	//		err = fmt.Errorf("setsockopt: %w", err)
	//		return
	//	}

	return
}

func (c *Connector) SendQueue() chan<- *proxy.ProxyMessage {
	return c.sendQueue
}

func (c *Connector) RecvQueue() <-chan *proxy.ProxyMessage {
	return c.recvQueue
}

func (c *Connector) recvLoop() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered in f", r)
		}
		c.wait.Done()
	}()

	dec := msgpack.NewDecoder(c.conn)
	for c.running {
		// Parse incoming message
		proxyData, err := dec.DecodeSlice()
		if err != nil {
			if err == io.EOF {
				break
			}
			fmt.Println("Decode Error", err)
			continue
		}

		if !c.running {
			break
		}

		proxyMessage := proxy.ProxyMessage{Type: proxy.MessageType(proxyData[0].(uint8)),
			Data: proxyData[1].([]byte)}

		c.recvQueue <- &proxyMessage
		// TODO add error message type
		//switch proxyMessage.Type {
		//case CanFrame:
		//	canmsg := new(can.Message)
		//	canmsg.Unmarshal(proxyMessage.Data)
		//	fmt.Println(canmsg)
		//}

	}
}

func (c *Connector) sendLoop() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered in f", r)
		}
		c.wait.Done()
	}()

	for c.running {
		select {
		case _ = <-c.stopSend:
			break
		case msg := <-c.sendQueue:
			msg_bytes, err := msg.Marshal()
			if err != nil {
				log.Println("Marshal error for packet")
				continue
			}
			c.conn.Write(msg_bytes)
		}
	}

}

//func (p *CanProxyClient) canToQueue(bus *can.Bus) {
//
//	for p.running {
//		select {
//		case _ = <-p.stopSend:
//			break
//		case msg := <-bus.RecvQueue():
//			if msg == nil {
//				break
//			}
//			b, err := MarshalCan(msg)
//			if err != nil {
//				fmt.Printf(
//					"Couldn't marshal CAN frame",
//				)
//				continue
//			}
//			p.clientQueue <- b[:]
//		}
//	}
//}
//
//
//func (c *Connector) handleIncoming(conn) {
//
//	dec := msgpack.NewDecoder(conn)
//
//	for true {
//
//		proxyData, err := dec.DecodeSlice()
//		if err != nil {
//			fmt.Println("Decode Error")
//		}
//		proxyMessage := proxy.ProxyMessage{Type: proxy.MessageType(proxyData[0].(uint8)),
//			Data: proxyData[1].([]byte)}
//
//		// TODO add error message type
//		switch proxyMessage.Type {
//		case proxy.CanFrame:
//			canmsg := new(can.Message)
//			canmsg.Unmarshal(proxyMessage.Data)
//			fmt.Println(canmsg)
//		}
//
//	}
//
//}
//
//func main() {
//
//	if len(os.Args) < 2 {
//		fmt.Fprintln(os.Stderr, "Please provide a gw server address")
//		return
//	}
//
//	addr := os.Args[1]
//
//	tcpAddr, err := net.ResolveTCPAddr("tcp", addr)
//	if err != nil {
//		println("ResolveTCPAddr failed:", err.Error())
//		os.Exit(1)
//	}
//
//	conn, err := net.DialTCP("tcp", nil, tcpAddr)
//	if err != nil {
//		println("Dial failed:", err.Error())
//		os.Exit(1)
//	}
//
//	go handleIncoming(conn)
//
//	canmsg := can.Message{
//		ArbitrationId: 20,
//		Data:          []byte("testing"),
//	}
//
//	m, err := proxy.MarshalCan(canmsg)
//	if err != nil {
//		fmt.Printf(
//			"Couldn't marshal CAN frame")
//	}
//
//	conn.Close()
//
//}
