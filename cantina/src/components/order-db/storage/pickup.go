package storage

import (
	"cantina/common/canopy"
	"cantina/common/canopy/fields"
	"cantina/common/cipher"
	"cantina/common/structs"
	"cantina/order-db/odb"
	"os"
	"path/filepath"
	"strconv"

	"github.com/vmihailenco/msgpack/v5"
)

type PickupReplyBuilder struct {
	Env *odb.Env
}

func (p *PickupReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
	state *canopy.SessionState,
) []byte {
	orderId := sessionId.GetId()
	orderFolder := filepath.Join(
		p.Env.DataDir,
		strconv.Itoa(int(orderId)),
	)

	// Initialize return object
	orderPickup := &structs.OrderPickup{}

	// Check if order folder exists
	if _, err := os.Stat(orderFolder); os.IsNotExist(err) {
		orderPickup.Status = 0
		orderPickup.Message = "Order folder does not exist"
		data, err := msgpack.Marshal(orderPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}

	// Try reading status
	status, err := os.ReadFile(filepath.Join(orderFolder, "status"))
	if err != nil {
		orderPickup.Status = 0
		orderPickup.Message = "Couldn't read order status"
		data, err := msgpack.Marshal(orderPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}
	statusNum, err := strconv.Atoi(string(status))
	if err != nil {
		orderPickup.Status = 0
		orderPickup.Message = "Couldn't parse order status"
		data, err := msgpack.Marshal(orderPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}


	// Open file for order status
	os.WriteFile(
		filepath.Join(orderFolder, "status"),
		[]byte("4"),
		0644,
	)

	// Try reading notes
	notes, err := os.ReadFile(filepath.Join(orderFolder, "notes"))
	if err != nil {
		orderPickup.Status = 0
		orderPickup.Message = "Couldn't read order notes"
		data, err := msgpack.Marshal(orderPickup)
		if err != nil {
			return []byte{}
		}
		return data
	}

	orderPickup.Status = uint32(statusNum)
	orderPickup.Message = string(notes)
	data, err := msgpack.Marshal(orderPickup)
	if err != nil {
		return []byte{}
	}

	return data
}

type PickupSessionInitializer struct {
	Env *odb.Env
}

func (p *PickupSessionInitializer) InitializeSession(
	sessionId fields.Session,
	state *canopy.SessionState,
) {
	// Set normal symmetric cipher as fallback
	state.SetSessionCipher(p.Env.SymmCipher)

	// Get order folder
	orderId := sessionId.GetId()
	orderFolder := filepath.Join(
		p.Env.DataDir,
		strconv.Itoa(int(orderId)),
	)

	// Check if order folder exists
	if _, err := os.Stat(orderFolder); os.IsNotExist(err) {
		return
	}

	// Try reading auth key
	key, err := os.ReadFile(filepath.Join(orderFolder, "auth"))
	if err != nil || len(key) != 32 {
		return
	}

	// Use custom cipher instead
	c := new(cipher.Cipher)
	c.Update(key)
	state.SetSessionCipher(c)
}
