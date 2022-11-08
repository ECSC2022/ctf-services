package main

import (
	"cantina/client/nes"
	"cantina/client/player"
	"fmt"
	"os"
)

func main() {

	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "Please provide a gw server address")
		return
	}

	addr := os.Args[1]

	apu := nes.NewAPU()
	player.Run(apu, addr)
	//APU.Step()
	println("hmm")
}
