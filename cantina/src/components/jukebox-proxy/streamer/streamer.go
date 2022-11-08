package streamer

import (
	"cantina/common/can"
	"encoding/binary"
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"time"
)

type Streamer struct {
	Log       *log.Logger
	sendQueue chan<- *can.Message
	uploadDir string
	play      bool
}

func NewStreamer(
	log *log.Logger,
	sendQueue chan<- *can.Message,
) (s *Streamer) {

	str := &Streamer{Log: log,
		sendQueue: sendQueue,
		uploadDir: "/data/uploads/",
	}
	return str
}

func SortFileNameDescend(files []string) {
	sort.Slice(files, func(i, j int) bool {
		return filepath.Base(files[i]) > filepath.Base(files[j])
	})
}

func (s *Streamer) HandleStreaming() {
	defer func() {
		if err := recover(); err != nil {
			s.Log.Println("panic occurred:", err)
		}
	}()

	_, err := os.ReadFile("./static/cantina.vgm")
	if err != nil {
		s.Log.Println("No cantina file. Not streaming", err)
		return
	}

	for {
		finished := make(chan bool)
		s.Log.Println("Starting Streamer")
		go s.runStreamer(finished)
		<-finished
		s.Log.Println("Streamer died")
		time.Sleep(1 * time.Second)
	}
}

func (s *Streamer) runStreamer(finished chan bool) {
	defer func() {
		if err := recover(); err != nil {
			s.Log.Println("panic occurred:", err)
		}
		finished <- true
	}()

	var file string
	for {
		files, _ := filepath.Glob(s.uploadDir + "*/*.vgm")
		if len(files) <= 0 {
			file = "./static/cantina.vgm"
		} else {
			SortFileNameDescend(files)
			rand.Seed(time.Now().Unix())
			n := rand.Intn(len(files))
			file = files[n]
		}
		s.Log.Println("Playing ", file)
		s.streamFile(file)
	}

}

func (s *Streamer) streamFile(filename string) {

	data, err := os.ReadFile(filename)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	clock := 1000000000 / 44100
	header_offset := 0x34
	vgm_data_offset := binary.LittleEndian.Uint32(data[0x34:0x38])
	index := int(vgm_data_offset) + header_offset

	regs := make([]byte, 0x20)
	regs[8] = 0xff

	prev := time.Now().UnixNano()
	dirty := 0
	var cmd byte
	var wait int
	var val byte
	var reg byte
	s.play = true
	for s.play {
		if index >= len(data) {
			s.play = false
			return
		}
		wait = 0
		cmd = data[index]
		index += 1
		switch cmd {
		case 0xB4:
			if index >= len(data)-1 {
				return
			}
			reg = data[index]
			val = data[index+1]
			index += 2
			if int(reg) >= len(regs) {
				s.Log.Println("Writing outside of register range")
				s.play = false
				return
			}
			regs[reg] = val
			dirty = dirty | (1 << reg)
		case 0x62:
			wait = 735
		case 0x63:
			wait = 882
		case 0x61:
			if index >= len(data)-2 {
				return
			}
			wait = int(binary.LittleEndian.Uint16(data[index : index+2]))
			index += 2
		case 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f:
			wait = int(cmd)&0xf + 1
		case 0x66:
			s.play = false
		default:
			s.Log.Println("Invalid Instruction", cmd)
			s.play = false
		}

		if (dirty > 0) && (wait > 0) {
			bs := make([]byte, 4)
			binary.LittleEndian.PutUint32(bs, uint32(dirty))
			bs = bs[:3]
			msg := can.Message{ArbitrationId: 0x666,
				Data: append(bs, regs...)}
			s.sendQueue <- &msg
			dirty = 0
		}

		if wait != 0 {
			diff := wait * clock
			now := time.Now().UnixNano()
			sleep := (int(prev) + diff) - int(now)
			time.Sleep(time.Duration(sleep) * time.Nanosecond)
			prev = now
		}

	}
}
