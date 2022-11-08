package controllers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type IndexController struct {
	db *gorm.DB
}

func NewIndexController(db *gorm.DB) *IndexController {
	return &IndexController{db: db}
}

func (c *IndexController) Index(ctx *gin.Context) {
	ctx.HTML(http.StatusOK, "index", gin.H{
		"title": "Index",
	})
}
