package structs

type Ticket struct {
	_msgpack struct{} `msgpack:",as_array"`
	TicketId uint32
	Timestamp uint32
}

type TicketSigned struct {
	_msgpack struct{} `msgpack:",as_array"`
	TicketData []byte
	Signature []byte
}
