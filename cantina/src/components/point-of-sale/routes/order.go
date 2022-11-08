package routes

import (
	"cantina/common/structs"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/vmihailenco/msgpack/v5"
)

const MAXIMUM_ORDER_AMOUNT uint32 = 30

func (rc *RouterContext) NewOrder(c *gin.Context) {
	// Parse transmitted order JSON
	var newOrder structs.Order
	if err := c.BindJSON(&newOrder); err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": fmt.Sprintf("Invalid order " +
				"JSON: %v",
				err,
			)},
		)
		return
	}

	// Verify order information. Make sure that there are no
	// non-existent items and that the maximum order amount is
	// not hit.
	if len(newOrder.OrderItems) == 0 {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": "No items ordered"},
		)
		return
	}

	// Check items and sum up amount
	orderTotal := uint32(0)
	for _, item := range newOrder.OrderItems {
		price, ok := rc.Env.OrderItems.PriceMap[item.ItemId]
		if !ok {
			msg := fmt.Sprintf(
				"Invalid item specified with ID: %d",
				item.ItemId,
			)
			c.JSON(
				http.StatusBadRequest,
				gin.H{"error": msg},
			)
			return
		}

		orderTotal += price
	}
	if orderTotal > MAXIMUM_ORDER_AMOUNT {
		msg := fmt.Sprintf(
			"Insufficient funds, maximum credits: %d",
			MAXIMUM_ORDER_AMOUNT,
		)
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": msg},
		)
		return
	}

	// Make sure ticket manager has keyserver public key
	rc.Env.TicketManager.SetPublicKey(
		rc.Env.KeyExchange.TicketSigningKey[:],
	)

	// Check ticket in order struct
	err := rc.Env.TicketManager.VerifyTicket(newOrder.Ticket)
	if err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": fmt.Sprintf(
				"Invalid ticket: %v",
				err,
			)},
		)
		return
	}

	// Serialize data into msgpack format
	data, err := msgpack.Marshal(&newOrder)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": "msgpack error"},
		)
		return
	}

	// Send order to order-db
	reply, err := rc.Env.OrderCreation.Send(data)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Error during " +
				"order creation: %v",
				err,
			)},
		)
		return
	}

	// Check if we encountered an error in the order DB
	if strings.HasPrefix(string(reply), "Err: ") {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": string(reply)[5:]},
		)
		return
	}

	// Parse reply received from order-DB
	var newOrderCreated structs.OrderCreated
	err = msgpack.Unmarshal(reply, &newOrderCreated)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Invalid reply " +
				"from Order-DB: %v",
				err,
			)},
		)
		return
	}

	c.JSON(http.StatusOK, &newOrderCreated)
}
