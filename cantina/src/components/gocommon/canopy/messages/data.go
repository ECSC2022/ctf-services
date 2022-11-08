package messages

import (
	"cantina/common/canopy/fields"
	"fmt"
)

type SessionData struct {
	SessionId  fields.Session
	Seq        fields.SequenceNumber
	cipherData fields.CipherData
}

func (s *SessionData) fields() []fields.Field {
	fieldList := [...]fields.Field{
		&s.SessionId,
		&s.Seq,
		&s.cipherData,
	}

	return fieldList[:]
}

func (s *SessionData) setFields(
	fieldList []fields.Field,
) (err error) {
	if len(fieldList) != 3 {
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

	seq, ok := fieldList[1].(*fields.SequenceNumber)
	if !ok {
		err = fmt.Errorf("Expected SequenceNumber")
		return
	}
	s.Seq = *seq

	cipherData, ok := fieldList[2].(*fields.CipherData)
	if !ok {
		err = fmt.Errorf("Expected CipherData")
		return
	}
	s.cipherData = *cipherData

	return
}
