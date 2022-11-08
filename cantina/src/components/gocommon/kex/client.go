package kex

import (
	"cantina/common/can"
	"cantina/common/cipher"
	"cantina/common/components"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"io"
	"log"
	"time"

	"golang.org/x/crypto/blake2s"
	"golang.org/x/crypto/chacha20poly1305"
	"golang.org/x/crypto/curve25519"
	"golang.org/x/crypto/hkdf"
)

type ClientIds struct {
	RecvPubkey    uint32
	RecvSymmetric uint32
	RecvRekey     uint32
	Request       uint32
}

type Client struct {
	cipher     *cipher.Cipher
	sendQueue  chan<- *can.Message
	messageIds ClientIds
	log *log.Logger
	stopLoop   chan interface{}
	privateKey [32]byte
	PublicKey  [32]byte
	KeyserverPublicKey [32]byte
	TicketSigningKey [32]byte
	DerivedKey []byte
}

func NewClient(
	cipher *cipher.Cipher,
	sendQueue chan<- *can.Message,
	messageIds ClientIds,
	log *log.Logger,
) (client *Client, err error) {
	// Generate private key
	random := rand.Reader
	var private [32]byte
	_, err = io.ReadFull(random, private[:])
	if err != nil {
		return
	}

	// Yay, magic from https://cr.yp.to/ecdh.html
	private[0] &= 248
	private[31] &= 127
	private[31] |= 64

	return NewClientDetached(
		cipher,
		sendQueue,
		private,
		messageIds,
		log,
	)
}

func NewClientDetached(
	cipher *cipher.Cipher,
	sendQueue chan<- *can.Message,
	keyBytes [32]byte,
	messageIds ClientIds,
	log *log.Logger,
) (client *Client, err error) {
	var public [32]byte

	// Calculate public key
	curve25519.ScalarBaseMult(&public, &keyBytes)
	client = &Client{
		cipher:     cipher,
		sendQueue:  sendQueue,
		messageIds: messageIds,
		log: log,
		stopLoop:   make(chan interface{}, 1),
		privateKey: keyBytes,
		PublicKey:  public,
		DerivedKey: nil,
	}
	return
}


func (c *Client) RecvHandlers() (
	handlers map[uint32]components.RecvHandler,
) {
	handlers = make(map[uint32]components.RecvHandler)
	handlers[c.messageIds.RecvPubkey] = func(
		canMsg *can.Message,
	) error {
		return c.recvKeyserverPublicKey(canMsg)
	}
	handlers[c.messageIds.RecvSymmetric] = func(
		canMsg *can.Message,
	) error {
		return c.recvSymmetricKey(canMsg)
	}
	handlers[c.messageIds.RecvRekey] = func(
		canMsg *can.Message,
	) error {
		return c.recvRekeyNotify(canMsg)
	}
	return
}

func (c *Client) UpdateLoop() {
	defer close(c.stopLoop)

	for {
		select {
		case _ = <-c.stopLoop:
			return
		case <-time.After(1 * time.Second):
			// TODO: Hmm... race condition i guess
			if c.DerivedKey == nil || !c.cipher.Ok() {
				c.sendPublicKey()
			}
		}
	}
}

func (c *Client) Shutdown() {
	go func() { c.stopLoop <- nil }()
}

func (c *Client) sendPublicKey() {
	publicKeyDigest := blake2s.Sum256(c.PublicKey[:])
	data := append(c.PublicKey[:], publicKeyDigest[:]...)
	c.sendQueue <- &can.Message{
		ArbitrationId: c.messageIds.Request,
		Data:          data,
	}
}

func (c *Client) recvKeyserverPublicKey(
	canMsg *can.Message,
) (err error) {
	if len(canMsg.Data) != 64 {
		err = fmt.Errorf(
			"Received invalid keyserver public key, "+
				"with length: %d",
			len(canMsg.Data),
		)
		return
	}

	// Store keyserver public key
	copy(c.KeyserverPublicKey[:], canMsg.Data[:32])
	copy(c.TicketSigningKey[:], canMsg.Data[32:])

	// Calculate shared key
	sharedKey, err := curve25519.X25519(
		c.privateKey[:],
		c.KeyserverPublicKey[:],
	)
	if err != nil {
		err = fmt.Errorf(
			"Could not calculate shared key: %w",
			err,
		)
		return
	}

	// Derive symmetric key
	hash := sha256.New
	info := []byte("keyserver-exch")
	hkdf := hkdf.New(hash, sharedKey[:], nil, info)
	derivedKey := make([]byte, chacha20poly1305.KeySize)
	if _, err = io.ReadFull(hkdf, derivedKey); err != nil {
		err = fmt.Errorf(
			"Could not derive symmetric key: %w",
			err,
		)
		return
	}

	// Don't directly assign the "make" above to the key, cause
	// the update loop is checking if the key is nil, so we
	// might get a race condition between "make" and the
	// key derivation. Therefore, we assign it here, after the
	// derivation.
	c.DerivedKey = derivedKey
	return
}

func (c *Client) recvSymmetricKey(
	canMsg *can.Message,
) (err error) {
	if c.DerivedKey == nil {
		err = fmt.Errorf(
			"No derived key has been established yet",
		)
		return
	}

	// Basic sanity check
	expectedMessageSize := chacha20poly1305.NonceSize +
		chacha20poly1305.Overhead +
		chacha20poly1305.KeySize
	if len(canMsg.Data) != expectedMessageSize {
		err = fmt.Errorf(
			"Unexpected message size for symmmetric "+
				"key receive message, expected %d, got %d ",
			expectedMessageSize,
			len(canMsg.Data),
		)
		return
	}

	// Initialize cipher with established derived key
	cipher, err := chacha20poly1305.New(c.DerivedKey)
	if err != nil {
		err = fmt.Errorf("Error creating cipher: %w", err)
		return
	}

	// Try to decrypt the shared symmetric key
	var symmetricKey []byte
	nonce := canMsg.Data[:chacha20poly1305.NonceSize]
	ciphertext := canMsg.Data[chacha20poly1305.NonceSize:]
	symmetricKey, err = cipher.Open(
		symmetricKey,
		nonce,
		ciphertext,
		nil,
	)
	if err != nil {
		// Can not decrypt it, because it doesn't belong to us
		err = nil
		return
	}

	c.cipher.Update(symmetricKey)
	c.log.Println("Shared key updated.")
	return
}

func (c *Client) recvRekeyNotify(canMsg *can.Message) (err error) {
	c.log.Println("Got rekey notification")
	if err = c.recvKeyserverPublicKey(canMsg); err != nil {
		return
	}

	c.sendPublicKey()
	return
}
