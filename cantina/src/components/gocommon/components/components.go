package components

import (
	"cantina/common/can"
)

type RecvHandler func(*can.Message) error
