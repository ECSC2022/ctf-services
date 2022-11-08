package udb

import (
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/kex"
	"log"
)

type Env struct {
	SymmCipher  *cipher.Cipher
	KeyExchange *kex.Client
	Log         *log.Logger

	JukeboxRequest      *canopy.Server
	JukeboxReplyBuilder canopy.ReplyBuilder

	UserRequest        *canopy.Server
	UserRequestBuilder canopy.ReplyBuilder
	UserRequestSession canopy.SessionInitialization

	DataDir string
}
