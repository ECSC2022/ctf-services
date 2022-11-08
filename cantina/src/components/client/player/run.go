package player

import (
	"log"
	"runtime"

	"github.com/gordonklaus/portaudio"

	"cantina/client/nes"
)

func init() {
	// we need a parallel OS thread to avoid audio stuttering
	runtime.GOMAXPROCS(2)

	// we need to keep OpenGL calls on a single thread
	//runtime.LockOSThread()
}

func Run(apu *nes.APU, serverAddress string) {
	// initialize audio
	portaudio.Initialize()
	defer portaudio.Terminate()

	audio := NewAudio()
	if err := audio.Start(); err != nil {
		log.Fatalln(err)
	}
	defer audio.Stop()

	apu.SetAudioChannel(audio.channel)
	apu.SetAudioSampleRate(audio.sampleRate)
	// run director
	director := NewDirector(audio, apu, serverAddress)
	director.Start()
}
