package routes

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type ProxyData struct {
	Data string `json:"data"`
}

type ProxyResp struct {
	Message string `json:"message"`
	Data    string `json:"data"`
}

func (rc *RouterContext) NewProxy(c *gin.Context) {
	// Parse transmitted order JSON
	var newReq ProxyData
	if err := c.BindJSON(&newReq); err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{"error": fmt.Sprintf("Invalid order "+
				"JSON: %v",
				err,
			)},
		)
		return
	}

	// Send request to user-db
	fmt.Println(newReq.Data)
	reply, err := rc.Env.UserDbRequest.Send([]byte(newReq.Data))
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{"error": fmt.Sprintf("Error during "+
				"user db request: %v",
				err,
			)},
		)
		return
	}

	c.JSON(http.StatusOK, gin.H{"data": reply})
}
