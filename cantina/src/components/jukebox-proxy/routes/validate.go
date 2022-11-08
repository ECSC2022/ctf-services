package routes

import (
	"encoding/base64"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type TicketData struct {
	Ticket string `json:"ticket"`
}

type TicketResp struct {
	Message string `json:"message"`
	Status  string `json:"status"`
}

func (rc *RouterContext) NewTicket(c *gin.Context) {
	// Parse transmitted order JSON
	var newTicket TicketData
	if err := c.BindJSON(&newTicket); err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"message": fmt.Sprintf("Invalid Ticket "+
				"JSON: %v",
				err,
			),
				"status": "ERR",
			},
		)
		return
	}

	// Make sure ticket manager has keyserver public key
	rc.Env.TicketManager.SetPublicKey(
		rc.Env.KeyExchange.TicketSigningKey[:],
	)

	// Check ticket in order struct

	rawTicket, err := base64.StdEncoding.DecodeString(newTicket.Ticket)
	if err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": fmt.Sprintf(
				"Invalid ticket: %v",
				err,
			),
				"status": "ERR",
			},
		)

	}

	err = rc.Env.TicketManager.VerifyTicket(rawTicket)
	if err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": fmt.Sprintf(
				"Invalid ticket: %v",
				err,
			),
				"status": "ERR",
			},
		)
		return
	}

	//	reply, err := rc.Env.UserDbRequest.Send([]byte(newReq.Data))
	//	if err != nil {
	//		c.JSON(
	//			http.StatusUnauthorized,
	//			gin.H{"error": fmt.Sprintf("Error during "+
	//				"user db request: %v",
	//				err,
	//			),
	//				"status": "ERR",
	//			},
	//		)
	//		return
	//	}

	//// Check if we encountered an error in the order DB
	//if strings.HasPrefix(string(reply), "Err: ") {
	//	c.JSON(
	//		http.StatusInternalServerError,
	//		gin.H{"error": string(reply)[5:]},
	//	)
	//	return
	//}

	// Parse reply received from order-DB
	//var newProxyResp ProxyResp
	//err = msgpack.Unmarshal(reply, &newProxyResp)
	//if err != nil {
	//	c.JSON(
	//		http.StatusInternalServerError,
	//		gin.H{"error": fmt.Sprintf("Invalid reply "+
	//			"from Order-DB: %v",
	//			err,
	//		)},
	//	)
	//	return
	//}

	c.JSON(http.StatusOK, gin.H{"message": "Ticket valid"})
}
