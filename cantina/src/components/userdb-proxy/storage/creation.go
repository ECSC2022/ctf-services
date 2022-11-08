package storage

import (
	"cantina/common/canopy/fields"
	"cantina/common/structs"
	"cantina/user-db/udb"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"sync"

	"github.com/vmihailenco/msgpack/v5"
)

type CreationReplyBuilder struct {
	Env       *udb.Env
	orderId   uint32
	orderLock sync.Mutex
}

func (c *CreationReplyBuilder) takeOrderId() (oid uint32, err error) {
	c.orderLock.Lock()
	defer c.orderLock.Unlock()

	// TODO: rollover is absurdely low for testing purposes,
	// fix this.
	oid = (c.orderId + 1) & 0xff

	// Write orderId to file, so we know where we left off
	orderIdFilePath := filepath.Join(c.Env.DataDir, "order_id")
	err = os.WriteFile(
		orderIdFilePath,
		[]byte(strconv.Itoa(int(oid))),
		0644,
	)
	if err != nil {
		return
	}

	c.orderId = oid
	return
}

func (c *CreationReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
) []byte {
	var newOrder structs.Order
	err := msgpack.Unmarshal(message, &newOrder)
	if err != nil {
		return []byte("Err: Invalid Order Data")
	}

	// Get a new order ID
	orderId, err := c.takeOrderId()
	if err != nil {
		return []byte("Err: Couldn't get order ID")
	}

	// Determine order folder and create it
	orderFolder := filepath.Join(
		c.Env.DataDir,
		strconv.Itoa(int(orderId)),
	)
	if err = os.Mkdir(orderFolder, 0755); err != nil {
		return []byte("Err: Couldn't create order dir")
	}

	// Generate auth key
	seed := rand.NewSource(int64(orderId))
	rand := rand.New(seed)
	var authKey [32]byte
	if _, err = rand.Read(authKey[:]); err != nil {
		return []byte("Err: Couldn't generate auth key")
	}
	err = os.WriteFile(
		filepath.Join(orderFolder, "auth"),
		authKey[:],
		0600,
	)
	if err != nil {
		return []byte("Err: Couldn't write auth key")
	}

	// Store order notes
	err = os.WriteFile(
		filepath.Join(orderFolder, "notes"),
		[]byte(newOrder.Notes),
		0644,
	)
	if err != nil {
		return []byte("Err: Couldn't store notes")
	}

	// Open file for order status
	err = os.WriteFile(
		filepath.Join(orderFolder, "status"),
		[]byte("0"),
		0644,
	)
	if err != nil {
		return []byte("Err: Couldn't store status")
	}

	// Send back orderId and authKey
	orderCreated := &structs.OrderCreated{
		OrderId: orderId,
		AuthKey: authKey[:],
	}
	data, err := msgpack.Marshal(orderCreated)
	if err != nil {
		return []byte("Err: Couldn't encode response")
	}

	return data
}
