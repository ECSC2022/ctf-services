package proxy

import (
	"bytes"
	"cantina/common/can"
	"encoding/binary"
	"fmt"

	"github.com/vmihailenco/msgpack/v5"
	"golang.org/x/sys/unix"
)

type MessageType uint8

const (
	Undefined MessageType = iota
	CanFrame
	CanFilter
	CanQuota
	CanToken
	CanError
)

func (s MessageType) String() string {
	switch s {
	case CanFrame:
		return "Can Frame"
	case CanFilter:
		return "Can filter list"
	case CanQuota:
		return "Message quota"
	case CanToken:
		return "Can access token"
	case CanError:
		return "Can Error"
	}
	return "unknown"
}

func MarshalCanMessage(msg *can.Message) (b []byte, err error) {
	dst := make([]byte, 8)
	// Check length
	dataLen := len(msg.Data)
	if dataLen > can.CANFD_MAX_PAYLOAD {
		err = fmt.Errorf(
			"CAN payload size too big, expected max %d"+
				", but got %d",
			can.CANFD_MAX_PAYLOAD,
			dataLen,
		)
		return
	}

	// TODO: Set EFF flag for ArbitrationId?
	if msg.ArbitrationId > 0x7FF {
		msg.ArbitrationId = msg.ArbitrationId | 0x80000000
	}
	binary.LittleEndian.PutUint32(dst[:4], msg.ArbitrationId)

	// uint8 DLC
	dst[4] = uint8(dataLen)
	// Padding: uint8 flags, res0, res1
	b = append(dst, msg.Data...)
	return
}

func UnmarshalCanMessage(msg *can.Message, frame []byte) (err error) {
	// Check length
	frameLen := len(frame)
	if frameLen > can.CANFD_MTU {
		err = fmt.Errorf(
			"CAN frame size is unexpected, expected "+
				"max %d, got %d",
			can.CANFD_MTU,
			frameLen,
		)
		return
	}

	canId := binary.LittleEndian.Uint32(frame[:4])
	canDlc := int(frame[4])
	canDlcEnd := 8 + canDlc

	// Check data length
	if frameLen < canDlcEnd {
		err = fmt.Errorf(
			"Invalid CAN DLC, expected a maximum of %d"+
				", but got %d",
			frameLen,
			canDlcEnd,
		)
		return
	}

	// Handle CAN cases based on extended ID flag
	if (canId & can.CAN_EFF_FLAG) != 0 {
		msg.ArbitrationId = canId & can.CAN_EXTENDED_MASK
	} else {
		msg.ArbitrationId = canId & can.CAN_STANDARD_MASK
	}

	msg.Data = frame[8:canDlcEnd]
	return
}

type ProxyMessage struct {
	_msgpack struct{} `msgpack:",as_array"`
	Type     MessageType
	Data     []byte
}

func (p *ProxyMessage) Marshal() (b []byte, err error) {
	b, err = msgpack.Marshal(p)
	return
}

// Can Frame
func NewProxyMessageCanFrame(msg *can.Message) (pmsg ProxyMessage, err error) {
	//	var frame [can.CANFD_MTU]byte
	frame, err := MarshalCanMessage(msg)
	if err != nil {
		return
	}

	pmsg = ProxyMessage{Type: CanFrame,
		Data: frame[:],
	}
	return
}

// CanQuota
func NewProxyMessageCanQuota(quota uint32) (pmsg ProxyMessage, err error) {
	bs := make([]byte, 4)
	binary.LittleEndian.PutUint32(bs, quota)
	pmsg = ProxyMessage{Type: CanQuota,
		Data: bs[:],
	}
	return
}

// CanFilter
func NewProxyMessageCanFilter(filters *[]unix.CanFilter) (pmsg ProxyMessage, err error) {

	var buf bytes.Buffer
	enc := msgpack.NewEncoder(&buf)
	enc.Encode(filters)
	pmsg = ProxyMessage{Type: CanFilter,
		Data: buf.Bytes(),
	}
	return
}

// CanToken
func NewProxyMessageCanToken(token *[]byte) (pmsg ProxyMessage, err error) {
	pmsg = ProxyMessage{Type: CanToken,
		Data: *token,
	}
	return
}

// CanError
func NewProxyMessageCanError(message *[]byte) (pmsg ProxyMessage, err error) {
	pmsg = ProxyMessage{Type: CanError,
		Data: *message,
	}
	return
}

//func Unmarshal(b []byte) (i interface{}, err error) {
//
//	pmsg = ProxyMessage{Type: CanFrame,
//		Data: frame[:],
//	}
//
//	err = msgpack.Unmarshal(pmsg)
//
//	return
//}

func MarshalCan(msg *can.Message) (b []byte, err error) {

	var frame [can.CANFD_MTU]byte
	err = msg.Marshal(&frame)
	if err != nil {
		return
	}

	pmsg := ProxyMessage{Type: CanFrame,
		Data: frame[:],
	}

	b, err = msgpack.Marshal(pmsg)

	return
}
