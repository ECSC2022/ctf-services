package proxy

import (
	"cantina/common/can"
	"cantina/common/tickets"
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"sync"

	"github.com/vmihailenco/msgpack/v5"
	"golang.org/x/sys/unix"
)

type CanProxyClient struct {
	canIf       string
	clientQueue chan *ProxyMessage
	stopSend    chan interface{}
	running     bool
	mu          sync.Mutex
	quota       int
	log         *log.Logger
	tm          *tickets.TicketManager
	msgLimit    int
}

func (p *CanProxyClient) GetQuota() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	q := p.quota
	return q
}

func (p *CanProxyClient) ResetQuota() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.quota = p.msgLimit
	q := p.quota
	return q
}

func (p *CanProxyClient) UseQuota(amount int) (err error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if (p.quota - amount) < 0 {
		err = errors.New("Not enough mana")
	} else {
		p.quota = p.quota - amount
	}
	return
}

func (p *CanProxyClient) canToQueue(ctx context.Context, bus *can.Bus) {

	for p.running {
		select {
		case _ = <-ctx.Done():
			break
		case msg := <-bus.RecvQueue():
			if msg == nil {
				break
			}
			b, err := NewProxyMessageCanFrame(msg)
			if err != nil {
				fmt.Printf(
					"Couldn't marshal CAN frame",
				)
				continue
			}
			p.clientQueue <- &b
		}
	}
}

func (p *CanProxyClient) queueToClient(ctx context.Context, conn net.Conn) {

	for p.running {
		select {
		case _ = <-ctx.Done():
			break
		case msg := <-p.clientQueue:
			b, _ := msg.Marshal()
			conn.Write(b)
		}
	}
}

func (p *CanProxyClient) proxyClient(ctx context.Context, conn net.Conn) {
	var err error
	var bus *can.Bus

	ctx, cancel := context.WithCancel(ctx)

	bus, err = can.NewBus(p.canIf)
	if err != nil {
		p.log.Printf(
			"Can't connect to '%s': %v",
			p.canIf,
			err,
		)
		return
	}

	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Panic:", r)
		}
		bus.Shutdown()
		cancel()
		p.running = false
		conn.Close()
		p.log.Println("Connection closed", conn.RemoteAddr())
	}()

	allow := unix.CanFilter{
		Id:   0x20000000,
		Mask: 0x1FFFF800,
	}
	err = bus.SetFilters(&[]unix.CanFilter{allow})
	if err != nil {
		fmt.Println("Error setting Filters")
	}

	go p.canToQueue(ctx, bus)
	go p.queueToClient(ctx, conn)

	dec := msgpack.NewDecoder(conn)
	for {
		// Parse incoming message
		proxyData, err := dec.DecodeSlice()
		if err != nil {
			if err == io.EOF {
				break
			}
			fmt.Println("Decode Error")
			break
		}
		p.handleMessage(proxyData, bus)
	}
}

func (p *CanProxyClient) handleMessage(proxyData []interface{}, bus *can.Bus) {

	var err error
	msg_type := Undefined
	switch proxyData[0].(type) {
	case uint8:
		msg_type = MessageType(proxyData[0].(uint8))
	case int8:
		msg_type = MessageType(proxyData[0].(int8))
	default:
		fmt.Println("Unknown Type")
	}

	// TODO add error message type
	switch msg_type {
	//Can Frame
	case CanFrame:
		data := proxyData[1].([]byte)
		err = p.UseQuota(1)
		if err != nil {
			conv_msg := []byte(err.Error())
			pmsg, err := NewProxyMessageCanError(&conv_msg)
			if err != nil {
				p.log.Println(err)
			}
			p.clientQueue <- &pmsg
			err = nil

		} else {
			canmsg := new(can.Message)
			err = UnmarshalCanMessage(canmsg, data)
			if err != nil {
				fmt.Println("Error", err)
				break
			}

			if canmsg.ArbitrationId < 0x800 {
				errmsg := []byte("Unauthorized")
				pmsg, err := NewProxyMessageCanError(&errmsg)
				if err != nil {
					p.log.Println(err)
				}
				p.clientQueue <- &pmsg
				break
			}

			bus.SendQueue() <- canmsg

			// Update clients current quota
			quota := p.GetQuota()
			pmsg, err := NewProxyMessageCanQuota(uint32(quota))
			if err != nil {
				p.log.Println(err)
			}
			p.clientQueue <- &pmsg
			err = nil
		}
	case CanToken:
		data := proxyData[1].([]byte)
		err := p.tm.VerifyTicket(data)
		if err != nil {
			fmt.Println(err)
			conv_msg := []byte(err.Error())
			pmsg, err := NewProxyMessageCanError(&conv_msg)
			if err != nil {
				p.log.Println(err)
			}
			p.clientQueue <- &pmsg
			err = nil
		} else {
			quota := p.ResetQuota()
			pmsg, err := NewProxyMessageCanQuota(uint32(quota))
			if err != nil {
				p.log.Println(err)
			}
			p.clientQueue <- &pmsg
		}

		// Can Filter Message
	case CanFilter:
		filters := proxyData[1].([]interface{})
		var newFilters []unix.CanFilter
		for _, filt := range filters {
			filtRaw := filt.([]interface{})
			canFilter := unix.CanFilter{
				Id:   TransToU32(filtRaw[0]),
				Mask: TransToU32(filtRaw[1]),
			}
			newFilters = append(newFilters, canFilter)
		}
		bus.SetFilters(&newFilters)
		if err != nil {
			fmt.Println("Error setting Filters")
		}
	}

}

func TransToU32(data interface{}) (res uint32) {
	switch data.(type) {
	case float64:
		res = uint32(data.(float64))
	case float32:
		res = uint32(data.(float32))
	case int64:
		res = uint32(data.(int64))
	case uint64:
		res = uint32(data.(uint64))
	case int32:
		res = uint32(data.(int32))
	case uint32:
		res = data.(uint32)
	case int8:
		res = uint32(data.(int8))
	case uint8:
		res = uint32(data.(uint8))
	case int:
		res = uint32(data.(int))
	case uint:
		res = uint32(data.(uint))
	}
	return
}
