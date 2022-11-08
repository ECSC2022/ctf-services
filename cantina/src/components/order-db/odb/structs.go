package odb

import (
	"cantina/common/canopy"
	"cantina/common/cipher"
	"cantina/common/kex"
	"log"
)

type Env struct {
	SymmCipher *cipher.Cipher
	KeyExchange *kex.Client
	Log *log.Logger

	OrderCreation *canopy.Server
	OrderCreationBuilder canopy.ReplyBuilder

	OrderPickup *canopy.Server
	OrderPickupBuilder canopy.ReplyBuilder
	OrderPickupSession canopy.SessionInitialization

	DataDir string
}
