//go:build linux

package can

import (
	"context"
	"fmt"
	"io/fs"
	"log"
	"net"
	"os"
	"syscall"

	"golang.org/x/sys/unix"
)

type Bus struct {
	file      *os.File
	fd        int
	sendQueue chan *Message
	stopSend  chan interface{}
	recvQueue chan *Message
	running   bool
	ctx       context.Context
	cancel    context.CancelFunc
}

func NewBus(ifaceName string) (bus *Bus, err error) {
	// Find interface
	iface, err := net.InterfaceByName(ifaceName)
	if err != nil {
		err = fmt.Errorf("interface %s: %w", ifaceName, err)
		return
	}

	// Check if network is up. Can technically still be a race
	// condition after this, but we're just using it for stability
	// purposes in the k8s environment.
	if (iface.Flags & net.FlagUp) == 0 {
		err = fmt.Errorf("interface %s is down", ifaceName)
		return
	}

	// Check if CAN-FD MTU is set
	if iface.MTU != CANFD_MTU {
		err = fmt.Errorf(
			"Expected CAN-FD MTU, got: %d",
			iface.MTU,
		)
		return
	}

	// Open CAN socket fd
	fd, err := unix.Socket(
		unix.AF_CAN,
		unix.SOCK_RAW,
		unix.CAN_RAW,
	)
	if err != nil {
		err = fmt.Errorf("socket: %w", err)
		return
	}

	// Put fd in non-blocking mode, so the created file will be
	// registered by the runtime poller
	// More info: https://morsmachine.dk/netpoller
	if err = unix.SetNonblock(fd, true); err != nil {
		err = fmt.Errorf("set nonblock: %w", err)
		return
	}

	// Enable CAN-FD frames
	err = syscall.SetsockoptInt(
		fd,
		unix.SOL_CAN_RAW,
		unix.CAN_RAW_FD_FRAMES,
		1,
	)
	if err != nil {
		err = fmt.Errorf("setsockopt: %w", err)
		return
	}

	// Bind socket to actual interface
	err = unix.Bind(fd, &unix.SockaddrCAN{Ifindex: iface.Index})
	if err != nil {
		err = fmt.Errorf("bind: %w", err)
		return
	}

	ctx, cancel := context.WithCancel(context.TODO())
	file := os.NewFile(uintptr(fd), ifaceName)
	bus = &Bus{
		file:      file,
		fd:        fd,
		sendQueue: make(chan *Message, 10),
		stopSend:  make(chan interface{}),
		running:   true,
		recvQueue: make(chan *Message, 10),
		ctx:       ctx,
		cancel:    cancel,
	}

	// Start receiving and sending loops
	go bus.recvLoop(ctx)
	go bus.sendLoop(ctx)

	return
}

func (b *Bus) Shutdown() {
	b.cancel()
	b.running = false
	close(b.recvQueue)
	close(b.stopSend)
	b.file.Close()
}

func (b *Bus) ResetFilters() (err error) {
	allow_all := unix.CanFilter{
		Id:   0,
		Mask: 0,
	}
	err = b.SetFilters(&[]unix.CanFilter{allow_all})
	return
}

func (b *Bus) SetFilters(filters *[]unix.CanFilter) (err error) {

	// Enable CAN-FD frames
	err = unix.SetsockoptCanRawFilter(
		b.fd,
		unix.SOL_CAN_RAW,
		unix.CAN_RAW_FILTER,
		*filters,
	)
	if err != nil {
		err = fmt.Errorf("setsockopt: %w", err)
		return
	}

	return
}

func (b *Bus) SendQueue() chan<- *Message {
	return b.sendQueue
}

func (b *Bus) RecvQueue() <-chan *Message {
	return b.recvQueue
}

func (b *Bus) recvLoop(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered in f", r)
		}
	}()
	for b.running {
		frame := make([]byte, CANFD_MTU)
		//		err := b.file.SetReadDeadline(time.Now().Add(2 * time.Second))
		//if err != nil {
		//	fmt.Println("Could not set timeout: ", err)
		//}
		n, err := b.file.Read(frame)

		if err != nil {
			switch err.(type) {
			case *fs.PathError:
				// File closed
				return
			default:
				log.Println("Unknown error occurred")

				panic(fmt.Errorf(
					"CANbus read error: %w",
					err,
				))

			}
		}

		// If we stopped while waiting, now is a good time
		// to quit
		if !b.running {
			return
		}

		// If we ran into the deadline without receiving
		// anything, read again
		if n == 0 {
			continue
		}

		msg := new(Message)
		if err := msg.Unmarshal(frame); err != nil {
			fmt.Printf("Invalid CAN Message: %v\n", err)
			continue
		}

		b.recvQueue <- msg
	}
}

func (b *Bus) sendLoop(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {

			fmt.Println(r)
		}
	}()

	for b.running {
		select {
		case _ = <-ctx.Done():
			close(b.sendQueue)
			break
		case msg := <-b.sendQueue:
			var frame [CANFD_MTU]byte
			err := msg.Marshal(&frame)
			if err != nil {
				fmt.Printf(
					"Couldn't marshal CAN frame",
				)
				continue
			}

			_, err = b.file.Write(frame[:])
			if err != nil {
				panic(fmt.Errorf(
					"CANbus write error: %w",
					err,
				))
			}
		}
	}
}
