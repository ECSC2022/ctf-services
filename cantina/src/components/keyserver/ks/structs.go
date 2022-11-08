package ks

import (
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/kex"
	"log"
)

type Env struct {
	SymmCipher *cipher.Cipher
	KeyExchange *kex.Server
	Log *log.Logger

	TicketCreation *canopy.Server
	TicketReplyBuilder canopy.ReplyBuilder

	DataDir string
}
