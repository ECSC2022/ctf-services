package routes

import (
	"net/http"
	"github.com/gin-gonic/gin"
)


func (rc *RouterContext) GetMenuItems(c *gin.Context) {
	c.JSON(http.StatusOK, rc.Env.OrderItems)
}
