package routes

import (
	"cantina/common/cipher"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
)

type powSolution struct {
	PowSolution uint64 `json:"pow-solution" binding:"required"`
}

func (rc *RouterContext) CreateTicket(c *gin.Context) {
	session := sessions.Default(c)

	// Parse PoW solution from JSON
	var newPowSolution powSolution
	if err := c.BindJSON(&newPowSolution); err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error": fmt.Sprintf("Invalid " +
					"PoW solution format: %v",
					err,
				),
			},
		)
		return
	}

	// Check if we have a valid PoW session
	rc.Env.SessionLock.RLock();
	target_wrapped := session.Get("pow-target")
	rc.Env.SessionLock.RUnlock();
	if target_wrapped == nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"error": "No valid PoW session " +
				"available, request new PoW.",
			},
		)
		return
	}
	target := target_wrapped.(uint64)


	// Check if the PoW is actually correct
	if newPowSolution.PowSolution != target {
		c.JSON(
			http.StatusBadGateway,
			gin.H{"error": "Invalid PoW solution"},
		)
		return
	}

	// Clear session to make sure they're not reusing the PoW
	// solution. Technically, this is probably a race condition.
	rc.Env.SessionLock.Lock();
	session.Clear()
	err := session.Save();
	rc.Env.SessionLock.Unlock();
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Could not " +
				"clear session: %v",
				err,
			)},
		)
		return
	}

	// Send a ticket creation request to the keyserver
	data, err := rc.Env.TicketCreation.Send(
		rc.Env.KeyExchange.PublicKey[:],
	)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Could not " +
				"create new ticket: %v",
				err,
			)},
		)
		return
	}

	// Check if we got an error
	if strings.HasPrefix(string(data), "Err:") {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Could not " +
				"create new ticket: %v",
				string(data),
			)},
		)
		return
	}

	// Decrypt the token sent by the keyserver
	derivedCipher := &cipher.Cipher{}
	derivedCipher.Update(rc.Env.KeyExchange.DerivedKey[:])
	token, err := derivedCipher.Decrypt(
		data[:12],
		data[12:],
		nil,
	)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Could not " +
				"decrypt ticket sent " +
				"by keyserver: %v",
				err,
			)},
		)
		return
	}

	c.JSON(http.StatusOK, gin.H{"ticket": token})
}
