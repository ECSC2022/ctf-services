package structs

type OrderItem struct {
	_msgpack struct{} `msgpack:",as_array" json:"-"`
	ItemId uint32 `json:"item_id" binding:"required"`
	Amount uint32 `json:"amount" binding:"required"`
}

type Order struct {
	_msgpack struct{} `msgpack:",as_array" json:"-"`
	OrderItems []OrderItem `json:"order_items" binding:"required"`
	Table uint32 `json:"table" binding:"required"`
	Notes string `json:"notes" binding:"required"`
	Ticket []byte `json:"ticket" binding:"required" msgpack:"-"`
}

type OrderCreated struct {
	_msgpack struct{} `msgpack:",as_array" json:"-"`
	OrderId uint32 `json:"order_id" binding:"required"`
	AuthKey []byte `json:"auth_key" binding:"required"`
}

type OrderPickup struct {
	_msgpack struct{} `msgpack:",as_array" json:"-"`
	Status uint32 `json:"status" binding:"required"`
	Message string `json:"message" binding:"required"`
}
