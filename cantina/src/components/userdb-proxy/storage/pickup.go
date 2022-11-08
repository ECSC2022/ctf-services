package storage

import (
	"cantina/common/canopy"
	"cantina/common/canopy/fields"
	"cantina/common/cipher"
	"cantina/common/structs"
	"cantina/user-db/udb"
	"os"
	"path/filepath"
	"strconv"

	"github.com/vmihailenco/msgpack/v5"
)

type PickupReplyBuilder struct {
	Env *udb.Env
}

func (p *PickupReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
) []byte {
	userId := sessionId.GetId()
	userFolder := filepath.Join(
		p.Env.DataDir,
		strconv.Itoa(int(userId)),
	)

	// Initialize return object
	userPickup := &structs.OrderPickup{}

	// Check if user folder exists
	if _, err := os.Stat(userFolder); os.IsNotExist(err) {
		userPickup.Status = 1
		userPickup.Message = "Order folder does not exist"
		data, err := msgpack.Marshal(userPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}

	// Try reading notes
	notes, err := os.ReadFile(filepath.Join(userFolder, "notes"))
	if err != nil {
		userPickup.Status = 2
		userPickup.Message = "Couldn't read user notes"
		data, err := msgpack.Marshal(userPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}

	userPickup.Status = 0
	userPickup.Message = string(notes)
	data, err := msgpack.Marshal(userPickup)
	if err != nil {
		return []byte{}
	}

	return data
}

type PickupSessionInitializer struct {
	Env *udb.Env
}

func (p *PickupSessionInitializer) InitializeSession(
	sessionId fields.Session,
	state *canopy.SessionState,
) {
	// Set normal symmetric cipher as fallback
	state.SetSessionCipher(p.Env.SymmCipher)

	// Get user folder
	userId := sessionId.GetId()
	userFolder := filepath.Join(
		p.Env.DataDir,
		strconv.Itoa(int(userId)),
	)

	// Check if user folder exists
	if _, err := os.Stat(userFolder); os.IsNotExist(err) {
		return
	}

	// Try reading auth key
	key, err := os.ReadFile(filepath.Join(userFolder, "auth"))
	if err != nil || len(key) != 32 {
		return
	}

	// Use custom cipher instead
	c := new(cipher.Cipher)
	c.Update(key)
	state.SetSessionCipher(c)
}
