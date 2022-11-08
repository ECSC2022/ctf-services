package cipher

import (
	"crypto/cipher"
	"crypto/rand"
	"errors"

	"golang.org/x/crypto/chacha20poly1305"
)

type Cipher struct {
	cipher    cipher.AEAD
	cipherOld cipher.AEAD
}

func (c *Cipher) Update(key []byte) (err error) {
	if key == nil || len(key) != chacha20poly1305.KeySize {
		err = errors.New("Invalid key")
		return
	}

	newCipher, err := chacha20poly1305.New(key)
	if err != nil {
		return
	}

	c.cipherOld = c.cipher
	c.cipher = newCipher
	return
}

func (c *Cipher) Encrypt(
	plaintext []byte,
	ad []byte,
) (nonceAndSealedData []byte, err error) {
	nonce := make([]byte, chacha20poly1305.NonceSize)
	_, err = rand.Read(nonce)
	if err != nil {
		return
	}

	nonceAndSealedData = append(nonceAndSealedData, nonce...)
	nonceAndSealedData = c.cipher.Seal(
		nonceAndSealedData,
		nonce,
		plaintext,
		ad,
	)
	return
}

func (c *Cipher) Decrypt(
	nonce []byte,
	ciphertext []byte,
	ad []byte,
) (plaintext []byte, err error) {
	if c.cipher == nil {
		err = errors.New("No cipher available")
		return
	}

	p, err := c.cipher.Open(plaintext, nonce, ciphertext, ad)
	if err == nil {
		plaintext = p
		return
	}

	// If we couldn't decrypt it, try with the old cipher
	if c.cipherOld == nil {
		return
	}

	plaintext, err = c.cipherOld.Open(
		plaintext,
		nonce,
		ciphertext,
		ad,
	)
	return
}

func (c *Cipher) Ok() bool {
	return c.cipher != nil
}
