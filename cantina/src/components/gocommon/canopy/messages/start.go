package messages

import (
	"cantina/common/canopy/fields"
	"fmt"
)

type SessionStart struct {
	SessionId  fields.Session
	Length     fields.MessageLength
	ExtraData  fields.ExtraData
	cipherData fields.CipherData
}

func (s *SessionStart) fields() []fields.Field {
	fieldList := [...]fields.Field{
		&s.SessionId,
		&s.Length,
		&s.ExtraData,
		&s.cipherData,
	}

	return fieldList[:]
}

func (s *SessionStart) setFields(
	fieldList []fields.Field,
) (err error) {
	if len(fieldList) != 4 {
		err = fmt.Errorf(
			"Wrong number of fields for SessionStart: %d",
			len(fieldList),
		)
		return
	}

	sessionId, ok := fieldList[0].(*fields.Session)
	if !ok {
		err = fmt.Errorf("Expected Session")
		return
	}
	s.SessionId = *sessionId

	length, ok := fieldList[1].(*fields.MessageLength)
	if !ok {
		err = fmt.Errorf("Expected MessageLength")
		return
	}
	s.Length = *length

	extraData, ok := fieldList[2].(*fields.ExtraData)
	if !ok {
		err = fmt.Errorf("Expected ExtraData")
		return
	}
	s.ExtraData = *extraData

	cipherData, ok := fieldList[3].(*fields.CipherData)
	if !ok {
		err = fmt.Errorf("Expected CipherData")
		return
	}
	s.cipherData = *cipherData

	return
}
