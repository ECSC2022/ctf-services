package structs

type Ticket struct {
	_msgpack  struct{} `msgpack:",as_array"`
	TicketId  uint32
	Timestamp uint32
}

type TicketSigned struct {
	_msgpack   struct{} `msgpack:",as_array"`
	TicketData []byte
	Signature  []byte
}

type FileTicket struct {
	_msgpack  struct{} `msgpack:",as_array"`
	TicketId  string
	Timestamp uint32
}

type SignedRequest struct {
	Data      string
	Signature string
}

type FileAccessRequest struct {
	Cmd    string
	Dir    string
	User   string
	File   string
	Ticket FileTicket
}
