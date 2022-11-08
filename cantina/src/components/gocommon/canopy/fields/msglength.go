package fields

import (
	"encoding/binary"
	"errors"
)

const mlSize = 2

type MessageLength struct {
	Value uint16
}

func (m MessageLength) FieldSize() int {
	return mlSize
}

func (m MessageLength) ToBytes(dst []byte) []byte {
	arr := [mlSize]byte{}
	binary.BigEndian.PutUint16(arr[:], m.Value)
	return append(dst, arr[:]...)
}

func (m *MessageLength) FromBytes(data []byte) (n int, err error) {
	if len(data) < m.FieldSize() {
		err = errors.New("Not enough data for MessageLength")
		return
	}

	m.Value = binary.BigEndian.Uint16(data[:mlSize])
	n = mlSize
	return
}
