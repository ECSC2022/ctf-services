package fields

import (
	"errors"

	"cantina/common/cipher"

	"golang.org/x/crypto/chacha20poly1305"
)

const cdSize = chacha20poly1305.NonceSize +
	chacha20poly1305.Overhead

type CipherData struct {
	nonce      [chacha20poly1305.NonceSize]byte
	ciphertext []byte
}

func (c *CipherData) FieldSize() int {
	return cdSize
}

func (c *CipherData) ToBytes(dst []byte) []byte {
	dst = append(dst, c.nonce[:]...)
	dst = append(dst, c.ciphertext...)
	return dst
}

func (c *CipherData) FromBytes(data []byte) (n int, err error) {
	if len(data) < cdSize {
		err = errors.New("Not enough data for CipherData")
		return
	}

	copy(c.nonce[:], data[:chacha20poly1305.NonceSize])
	c.ciphertext = make(
		[]byte,
		len(data)-chacha20poly1305.NonceSize,
	)
	copy(c.ciphertext, data[chacha20poly1305.NonceSize:])
	n = len(data)
	return
}

func (c *CipherData) ToPlainText(
	cipher *cipher.Cipher,
	associatedData []byte,
) ([]byte, error) {
	return cipher.Decrypt(c.nonce[:], c.ciphertext, associatedData)
}

func CipherDataFromPlaintext(
	cipher *cipher.Cipher,
	plaintext []byte,
	associatedData []byte,
) (c CipherData, err error) {
	bytes, err := cipher.Encrypt(plaintext, associatedData)
	if err != nil {
		return
	}

	_, err = c.FromBytes(bytes)
	return
}
