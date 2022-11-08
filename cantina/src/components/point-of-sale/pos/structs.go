package pos

import (
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/kex"
	"cantina/common/tickets"
	"log"
	"sync"
)

type Env struct {
	SymmCipher *cipher.Cipher
	KeyExchange *kex.Client
	OrderCreation *canopy.Client
	TicketCreation *canopy.Client
	Log *log.Logger
	OrderItems *ItemOverview
	TicketManager *tickets.TicketManager
	GamebotPubKey []byte
	SessionLock sync.RWMutex
}
