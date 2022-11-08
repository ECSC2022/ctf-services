package jukebox

import (
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/kex"
	"cantina/common/tickets"
	"cantina/jukebox/streamer"
	jtickets "cantina/jukebox/tickets"
	"log"
)

type Env struct {
	SymmCipher  *cipher.Cipher
	KeyExchange *kex.Client
	Log         *log.Logger

	UserDbRequest *canopy.Client

	JukeboxRequest      *canopy.Server
	JukeboxReplyBuilder canopy.ReplyBuilder

	UserRequest        *canopy.Server
	UserRequestBuilder canopy.ReplyBuilder
	UserRequestSession canopy.SessionInitialization

	TicketManager     *tickets.TicketManager
	UserTicketManager *jtickets.UserTicketManager

	Streamer *streamer.Streamer

	DataDir string
}
