package fields

import (
	"errors"
)

const edSize = 30

type ExtraData struct {
	Value []byte
}

func (e ExtraData) FieldSize() int {
	return edSize
}

func (e ExtraData) ToBytes(dst []byte) []byte {
	data := make([]byte, edSize)
	if len(e.Value) > 0 {
		copy(data, e.Value[:])
	}
	return append(dst, data...)
}

func (e *ExtraData) FromBytes(data []byte) (n int, err error) {
	if len(data) < edSize {
		err = errors.New("Not enough data for ExtraData")
		return
	}
	
	e.Value = make([]byte, edSize)
	copy(e.Value, data[:edSize])
	n = edSize
	return
}
