package fields

import (
	"errors"
)

const seqSize = 1

type SequenceNumber struct {
	Value uint8
}

func (s SequenceNumber) FieldSize() int {
	return seqSize
}

func (s SequenceNumber) ToBytes(dst []byte) []byte {
	arr := [seqSize]byte{}
	arr[0] = s.Value
	return append(dst, arr[:]...)
}

func (s *SequenceNumber) FromBytes(data []byte) (n int, err error) {
	if len(data) < s.FieldSize() {
		err = errors.New("Not enough data for SequenceNumber")
		return
	}

	s.Value = data[:seqSize][0]
	n = seqSize
	return
}
