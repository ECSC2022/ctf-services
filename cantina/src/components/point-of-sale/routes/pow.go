package routes

import (
	"cantina/common/pow"
	"fmt"
	"net/http"

	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
)

func (rc *RouterContext) CreatePow(c *gin.Context) {
	session := sessions.Default(c)

	// Generate a new PoW
	proof, target, err := pow.NewPoW(
		21,
		rc.Env.GamebotPubKey,
		rc.Env.Log,
	)
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf(
				"Unable to generate PoW: %v",
				err,
			)},
		)
		return
	}

	// Store the PoW target in the session
	// Currently, we're just overriding the session target with
	// a new PoW, we could theoretically do it the other way
	// around and check if we already have an existing session.
	rc.Env.SessionLock.Lock()
	session.Set("pow-target", target)
	session.Options(sessions.Options{
		MaxAge: 120, // Sessions expire after 120 seconds
	})
	err = session.Save()
	rc.Env.SessionLock.Unlock()
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf(
				"Unable to store session: %v",
				err,
			)},
		)
		return
	}

	// Return proof as JSON
	c.JSON(http.StatusOK, &proof)
}
