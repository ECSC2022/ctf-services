package proxy

import (
	"cantina/common/tickets"
	"context"
	"log"
	"net"
	"os"
	"strconv"
)

type CanProxy struct {
	canIf string
	host  string
	log   *log.Logger
	tm    *tickets.TicketManager
}

func NewCanProxy(
	canIf string,
	host string,
	log *log.Logger,
	tm *tickets.TicketManager,

) (canProxy *CanProxy, err error) {
	canProxy = &CanProxy{
		canIf: canIf,
		host:  host,
		log:   log,
		tm:    tm,
	}
	return
}

func newCanProxyClient(
	canIf string,
	log *log.Logger,
	tm *tickets.TicketManager,
	msgLimit int,

) (canProxy *CanProxyClient, err error) {
	canProxy = &CanProxyClient{
		canIf:       canIf,
		running:     true,
		clientQueue: make(chan *ProxyMessage),
		stopSend:    make(chan interface{}),
		log:         log,
		tm:          tm,
		msgLimit:    msgLimit,
	}
	return
}

func (p *CanProxy) Start(ctx context.Context) {

	canMsgLimit := 257
	val, ok := os.LookupEnv("GATEWAY_TICKET_LIMIT")
	if ok {
		conv, err := strconv.Atoi(val)
		if err != nil {
			log.Println("wrong GATEWAY_TICKET_LIMIT format")
			panic(err)
		}
		canMsgLimit = conv
	}

	listener, err := net.Listen("tcp", p.host)
	if err != nil {
		panic(err)
	}

	for {
		conn, err := listener.Accept()
		p.log.Println("New connection", conn.RemoteAddr())
		if err != nil {
			log.Println("error accepting connection", err)
			continue
		}
		newP, err := newCanProxyClient(p.canIf, p.log, p.tm, canMsgLimit)
		go newP.proxyClient(ctx, conn)

		//		var m runtime.MemStats
		//		runtime.ReadMemStats(&m)
		//		log.Printf("\nAlloc = %v\nTotalAlloc = %v\nSys = %v\nNumGC = %v\n\n", m.Alloc/1024, m.TotalAlloc/1024, m.Sys/1024, m.NumGC)
		//
		//		fmt.Println(runtime.NumGoroutine())
	}
}
