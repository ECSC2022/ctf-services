package kex

import (
	"bytes"
	"cantina/common/can"
	"cantina/common/cipher"
	"cantina/common/components"
	"crypto/ed25519"
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

type ServerIds struct {
	PubkeyBroadcast uint32
	ShareSymmetric  uint32
	RekeyNotify     uint32
	Request         uint32
	SymmetricReq    map[uint32]string
	RekeyReq        map[uint32]string
}

type Server struct {
	cipher     *cipher.Cipher
	sendQueue  chan<- *can.Message
	messageIds ServerIds
	log *log.Logger
	stopLoop   chan interface{}

	PrivateKey [curve25519.ScalarSize]byte
	PublicKey  [curve25519.ScalarSize]byte
	SigningKey ed25519.PrivateKey
	signingKeyPublic ed25519.PublicKey

	symmetricKey [chacha20poly1305.KeySize]byte
	resyncInterval time.Duration
}

func NewServer(
	cipher *cipher.Cipher,
	sendQueue chan<- *can.Message,
	messageIds ServerIds,
	storedPrivateKey []byte,
	storedSigningKey []byte,
	resyncInterval time.Duration,
	log *log.Logger,
) (server *Server, err error) {
	random := rand.Reader

	// Generate first symmetric key
	var symmetricKey [chacha20poly1305.KeySize]byte
	_, err = rand.Read(symmetricKey[:])
	if err != nil {
		return
	}
	cipher.Update(symmetricKey[:])

	// Generate private key
	var private, public [32]byte
	if len(storedPrivateKey) != curve25519.ScalarSize {
		_, err = io.ReadFull(random, private[:])
		if err != nil {
			return
		}
	} else {
		copy(private[:], storedPrivateKey)
	}

	// Yay, magic from https://cr.yp.to/ecdh.html
	private[0] &= 248
	private[31] &= 127
	private[31] |= 64

	// Calculate public key
	curve25519.ScalarBaseMult(&public, &private)

	// Generate private key for signing
	var signingKey ed25519.PrivateKey
	var signingKeyPublic ed25519.PublicKey
	if len(storedSigningKey) != ed25519.PrivateKeySize {
		signingKeyPublic, signingKey, err = 
			ed25519.GenerateKey(rand.Reader)
		if err != nil {
			return
		}
	} else {
		signingKey = append(signingKey, storedSigningKey...)
		signingKeyPublic =
			signingKey.Public().(ed25519.PublicKey)
	}

	server = &Server{
		cipher:     cipher,
		sendQueue:  sendQueue,
		messageIds: messageIds,
		log: log,
		stopLoop:   make(chan interface{}, 1),

		PrivateKey: private,
		PublicKey:  public,
		SigningKey: signingKey,
		signingKeyPublic: signingKeyPublic,

		symmetricKey: symmetricKey,
		resyncInterval: resyncInterval,
	}
	return
}

func (s *Server) RecvHandlers() (
	handlers map[uint32]components.RecvHandler,
) {
	handlers = make(map[uint32]components.RecvHandler)
	handlers[s.messageIds.Request] = func(
		canMsg *can.Message,
	) error {
		return s.recvPublicKeyRequest(canMsg)
	}

	// Key exchange listeners
	for mid := range s.messageIds.SymmetricReq {
		handlers[mid] = func(canMsg *can.Message) error {
			return s.recvSymmetricRequest(canMsg)
		}
	}

	// Rekeying listeners
	for mid := range s.messageIds.RekeyReq {
		handlers[mid] = func(canMsg *can.Message) error {
			return s.recvRekeyRequest(canMsg)
		}
	}
	return
}

func (s *Server) UpdateLoop() {
	defer close(s.stopLoop)

	for {
		select {
		case _ = <-s.stopLoop:
			return
		case <-time.After(s.resyncInterval):
			// New symmetric key
			var symmetricKey [chacha20poly1305.KeySize]byte
			_, err := rand.Read(symmetricKey[:])
			if err != nil {
				s.log.Println(
					"Could not generate " +
					"new symmetric key.",
				)
				continue
			}

			// Send out new key, then update our own cipher 
			s.log.Println("Sending re-key notification")
			s.sendRekey()

			// This key is used for the keyserver's own
			// canopy sessions
			s.cipher.Update(symmetricKey[:])

			// This key is sent out
			s.symmetricKey = symmetricKey 
		}
	}
}

func (s *Server) Shutdown() {
	go func() { s.stopLoop <- nil }()
}

func (s *Server) SignData(data []byte) (sig []byte) {
	sig = ed25519.Sign(s.SigningKey, data)
	return
}

func (s *Server) DeriveSharedSecret(publicKey []byte) (
	derivedKey [chacha20poly1305.KeySize]byte,
	err error,
) {
	// Calculate shared key
	sharedKey, err := curve25519.X25519(
		s.PrivateKey[:],
		publicKey,
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
	if _, err = io.ReadFull(hkdf, derivedKey[:]); err != nil {
		err = fmt.Errorf(
			"Could not derive symmetric key: %w",
			err,
		)
		return
	}
	return
}

func (s *Server) sendRekey() {
	var data []byte
	data = append(data, s.PublicKey[:]...)
	data = append(data, s.signingKeyPublic[:]...)

	s.sendQueue<- &can.Message{
		ArbitrationId: s.messageIds.RekeyNotify,
		Data: data,
	}
}

func (s *Server) sendPublicKey() {
	var data []byte
	data = append(data, s.PublicKey[:]...)
	data = append(data, s.signingKeyPublic[:]...)

	s.sendQueue<- &can.Message{
		ArbitrationId: s.messageIds.PubkeyBroadcast,
		Data: data,
	}
}

func (s *Server) sendSymmetric(
	msg *can.Message,
	sendPubkey bool,
) (err error) {
        // A peer sent us (hopefully) a public key, so we're gonna
        // respond with our pubkey (for now we're just broadcasting it,
        // not sure if we can reduce the number of pubkey messages?)
        // and send an authenticated encrypted message with the
        // shared symmetric key.

        // Before we broadcast the pubkey, check if the message is
        // somewhat sane first.
	if len(msg.Data) != 64 {
		err = fmt.Errorf("Received message with invalid len")
		return
	}
	key := msg.Data[:32]
	keyHash := msg.Data[32:]
	keyDigest := blake2s.Sum256(key)
	if bytes.Compare(keyDigest[:], keyHash) != 0 {
		err = fmt.Errorf(
			"Received public key with invalid hash",
		)
		return
	}

	// Setup cipher and encrypt the shared symmetric key
	derivedKey, err := s.DeriveSharedSecret(key)
	if err != nil {
		err = fmt.Errorf("Couldn't derive shared secret")
		return
	}
	cipher, err := chacha20poly1305.New(derivedKey[:])
	if err != nil {
		err = fmt.Errorf("Couldn't initialize cipher: %w", err)
		return
	}

	// Read nonce
	var nonce [chacha20poly1305.NonceSize]byte
	_, err = rand.Read(nonce[:])
	if err != nil {
		err = fmt.Errorf("Couldn't generate nonce: %w", err)
		return
	}

	// Encrypt symmetric key
	var ct []byte
	ct = append(ct, nonce[:]...)
	ct = cipher.Seal(ct, nonce[:], s.symmetricKey[:], nil)

	// Check if we have to send the public key
	if sendPubkey {
		s.sendPublicKey()
	}

	// Send encrypted message
	s.sendQueue <- &can.Message{
		ArbitrationId: s.messageIds.ShareSymmetric,
		Data:          ct,
	}

	return
}

func (s *Server) recvPublicKeyRequest(canMsg *can.Message) error {
	if len(canMsg.Data) == 0 {
		s.sendPublicKey()
	}

	return nil
}

func (s *Server) recvSymmetricRequest(canMsg *can.Message) error {
	return s.sendSymmetric(canMsg, true)
}

func (s *Server) recvRekeyRequest(canMsg *can.Message) error {
	return s.sendSymmetric(canMsg, false)
}
