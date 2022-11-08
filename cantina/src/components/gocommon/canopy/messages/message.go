package messages

import (
	"cantina/common/can"
	"cantina/common/canopy/fields"
	"cantina/common/cipher"
	"fmt"
)

type SessionMessage interface {
	fields() []fields.Field
	setFields([]fields.Field) error
}

func SessionMessageToCan(
	sessionMsg SessionMessage,
	arbitrationId uint32,
) (c *can.Message, err error) {
	c = new(can.Message)
	c.ArbitrationId = arbitrationId

	for _, field := range sessionMsg.fields() {
		c.Data = field.ToBytes(c.Data)
	}

	if len(c.Data) > can.CANFD_MAX_PAYLOAD {
		err = fmt.Errorf(
			"session message bigger than allowed: %d",
			len(c.Data),
		)
	}

	return
}

func SessionMessageFromCan(
	sessionMsg SessionMessage,
	canMsg *can.Message,
) (err error) {
	var n int
	offset := 0

	for _, field := range sessionMsg.fields() {
		n, err = field.FromBytes(canMsg.Data[offset:])
		if err != nil {
			return
		}

		offset += n
	}

	return
}

func SessionMessageFromPlaintext(
	sessionMsg SessionMessage,
	cipher *cipher.Cipher,
	plaintext []byte,
	associatedFields ...fields.Field,
) (err error) {
	var associatedData []byte

	for _, field := range associatedFields {
		associatedData = field.ToBytes(associatedData)
	}

	c, err := fields.CipherDataFromPlaintext(
		cipher,
		plaintext,
		associatedData,
	)

	associatedFields = append(associatedFields, &c)
	err = sessionMsg.setFields(associatedFields)
	return
}

func SessionMessageToPlaintext(
	sessionMsg SessionMessage,
	cipher *cipher.Cipher,
) (plaintext []byte, err error) {
	var associatedData []byte
	var cipherData *fields.CipherData

	for _, field := range sessionMsg.fields() {
		if c, ok := field.(*fields.CipherData); ok {
			cipherData = c
		} else {
			associatedData = field.ToBytes(associatedData)
		}
	}

	if cipherData == nil {
		err = fmt.Errorf("SesionMessage has no CipherData")
		return
	}

	plaintext, err = cipherData.ToPlainText(cipher, associatedData)
	return
}

func SessionMessageMinLength(
	sessionMsg SessionMessage,
) (length int) {
	for _, field := range sessionMsg.fields() {
		length += field.FieldSize()
	}
	return
}
