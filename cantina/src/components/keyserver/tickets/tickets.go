package tickets

import (
	"cantina/common/canopy"
	"cantina/common/canopy/fields"
	"cantina/common/structs"
	"cantina/keyserver/ks"
	"crypto/rand"
	"encoding/binary"
	"time"

	"github.com/vmihailenco/msgpack/v5"
	"golang.org/x/crypto/chacha20poly1305"
)

type TicketReplyBuilder struct {
	Env *ks.Env
}

func (t *TicketReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
	state *canopy.SessionState,
) []byte {
	// Generate tokenId
	ticketId := make([]byte, 4)
	_, err := rand.Read(ticketId)
	if err != nil {
		return []byte("Err: Couldn't generate tokenId")
	}

	// Create token data
	ticketData := structs.Ticket{
		TicketId:  binary.BigEndian.Uint32(ticketId),
		Timestamp: uint32(time.Now().Unix()),
	}
	ticketDataBytes, err := msgpack.Marshal(&ticketData)
	if err != nil {
		return []byte("Err: Couldn't marshal ticketData")
	}
	signature := t.Env.KeyExchange.SignData(ticketDataBytes)

	// Finalize ticket
	ticketSigned := structs.TicketSigned{
		TicketData: ticketDataBytes,
		Signature:  signature,
	}
	ticket, err := msgpack.Marshal(&ticketSigned)
	if err != nil {
		return []byte("Err: Couldn't marshal ticketSigned")
	}

	// Get derived key
	derive, err := t.Env.KeyExchange.DeriveSharedSecret(message)
	if err != nil {
		return []byte("Err: Couldn't derive shared secret")
	}

	// Get nonce
	nonce := make([]byte, chacha20poly1305.NonceSize)
	_, err = rand.Read(nonce)
	if err != nil {
		return []byte("Err: Couldn't generate nonce")
	}

	// Encrypt ticket for transmission
	cipher, err := chacha20poly1305.New(derive[:])
	if err != nil {
		return []byte("Err: Couldn't intialize AEAD")
	}
	var ct []byte
	ct = append(ct, nonce...)
	return cipher.Seal(
		ct,
		nonce,
		ticket,
		nil,
	)
}
