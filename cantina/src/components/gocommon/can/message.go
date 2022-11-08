package can

import (
	"encoding/binary"
	"fmt"
)

type Message struct {
	ArbitrationId uint32
	Data          []byte
}

func (msg *Message) Marshal(
	dst *[CANFD_MTU]byte,
) (err error) {
	// Check length
	dataLen := len(msg.Data)
	if dataLen > CANFD_MAX_PAYLOAD {
		err = fmt.Errorf(
			"CAN payload size too big, expected max %d"+
				", but got %d",
			CANFD_MAX_PAYLOAD,
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
	copy(dst[8:], msg.Data)
	return
}

func (msg *Message) Unmarshal(frame []byte) (err error) {
	// Check length
	frameLen := len(frame)
	if frameLen != CAN_MTU && frameLen != CANFD_MTU {
		err = fmt.Errorf(
			"CAN frame size is unexpected, expected "+
				"%d or %d, got %d",
			CAN_MTU,
			CANFD_MTU,
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
	if (canId & CAN_EFF_FLAG) != 0 {
		msg.ArbitrationId = canId & CAN_EXTENDED_MASK
	} else {
		msg.ArbitrationId = canId & CAN_STANDARD_MASK
	}

	msg.Data = frame[8:canDlcEnd]
	return
}
