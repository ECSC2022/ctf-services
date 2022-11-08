package player

import (
	"encoding/binary"
	"fmt"
	"net"
	"os"

	"cantina/client/nes"
	"cantina/common/can"
	"cantina/gateway/proxy"
	"time"

	"github.com/vmihailenco/msgpack"
)

type CanFrame struct {
	Can_id uint32
	Length uint8
	Flags  uint8
	Res0   uint8
	Res1   uint8
	Data   [64]byte
}

type Director struct {
	audio     *Audio
	apu       *nes.APU
	timestamp float64
	servAddr  string
	init_apu  bool
}

func NewDirector(audio *Audio, apu *nes.APU, servAddr string) *Director {
	director := Director{}
	director.audio = audio
	director.apu = apu
	director.servAddr = servAddr
	director.init_apu = true
	return &director
}

func (director *Director) StepSeconds(seconds float64) {
	cycles := int(nes.CPUFrequency * seconds)
	for i := 0; i < cycles; i++ {
		director.apu.Step()
	}
}

func (d *Director) Step() {
	timestamp := float64(time.Now().UnixNano()) / 1000000000
	dt := timestamp - d.timestamp
	d.timestamp = timestamp
	if dt > 1 {
		dt = 0
	}
	d.StepSeconds(dt)
}

func (d *Director) Start() {
	d.Run()
}

func (d *Director) handleCan(msg *can.Message) {

	fmt.Println("Can Message")
	fmt.Println(msg)
	if msg.ArbitrationId == 0x77777 {
		dirty := make([]byte, 4)
		dirty[0] = msg.Data[0]
		dirty[1] = msg.Data[1]
		dirty[2] = msg.Data[2]
		dirty[3] = 0
		values := binary.LittleEndian.Uint32(dirty)
		for i, c := range msg.Data[3:] {
			if d.init_apu || ((values)&(1<<i)) > 1 {
				d.apu.WriteRegister(uint16(0x4000+i), c)
			}
		}
		d.init_apu = false
	}
	d.Step()

}

func (d *Director) Run() {
	tcpAddr, err := net.ResolveTCPAddr("tcp", d.servAddr)
	if err != nil {
		println("ResolveTCPAddr failed:", err.Error())
		os.Exit(1)
	}

	conn, err := net.DialTCP("tcp", nil, tcpAddr)
	if err != nil {
		println("Dial failed:", err.Error())
		os.Exit(1)
	}

	//init_apu := true

	dec := msgpack.NewDecoder(conn)

	for true {

		proxyData, err := dec.DecodeSlice()
		if err != nil {
			fmt.Println("Decode Error")
		}
		proxyMessage := proxy.ProxyMessage{Type: proxy.MessageType(proxyData[0].(uint8)),
			Data: proxyData[1].([]byte)}

		// TODO add error message type
		switch proxyMessage.Type {
		case proxy.CanFrame:
			data := make([]byte, 72)
			copy(data[:], proxyMessage.Data[:])
			proxyMessage.Data = data[:]
			canmsg := new(can.Message)
			canmsg.Unmarshal(proxyMessage.Data)
			d.handleCan(canmsg)
		}

	}
	conn.Close()

	//	for !d.window.ShouldClose() {
	//		d.window.SwapBuffers()
	//		glfw.PollEvents()
	//	}
	//
	// d.SetView(nil)
}
