package fields

import (
	"crypto/rand"
	"encoding/binary"
	"errors"
)

const sessSize = 4

type Session struct {
	value uint32
}

func NewSession() (s Session, err error) {
	arr := [4]byte{}
	_, err = rand.Read(arr[:])
	if err != nil {
		return
	}

	s.value = binary.LittleEndian.Uint32(arr[:])
	return
}

func (s Session) FieldSize() int {
	return sessSize
}

func (s Session) ToBytes(dst []byte) []byte {
	arr := [sessSize]byte{}
	binary.BigEndian.PutUint32(arr[:], s.value)
	return append(dst, arr[:]...)
}

func (s *Session) FromBytes(data []byte) (n int, err error) {
	if len(data) < sessSize {
		err = errors.New("Not enough data for session")
		return
	}

	s.value = binary.BigEndian.Uint32(data[:sessSize])
	n = sessSize
	return
}

func (s *Session) GetId() uint32 {
	return s.value
}
