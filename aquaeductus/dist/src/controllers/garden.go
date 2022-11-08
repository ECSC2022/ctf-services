package controllers

import (
	"errors"
	"fmt"
	"net/http"

	"aquaeductus/models"
	"github.com/gin-gonic/gin"
	"github.com/speps/go-hashids/v2"
	"gorm.io/gorm"
)

type GardenController struct {
	db  *gorm.DB
	hid *hashids.HashID
}

func NewGardenController(db *gorm.DB, hid *hashids.HashID) *GardenController {
	return &GardenController{db: db, hid: hid}
}

func findGarden(ctx *gin.Context, hid *hashids.HashID, db *gorm.DB) (*models.Garden, error) {
	var params struct {
		ID string `uri:"id" binding:"required,min=8,max=32"`
	}
	if err := ctx.ShouldBindUri(&params); err != nil {
		return nil, nil
	}

	ids, err := hid.DecodeInt64WithError(params.ID)
	if err != nil || len(ids) != 1 {
		return nil, nil
	}

	var garden models.Garden
	if result := db.WithContext(ctx).Preload("User").Where("`id` = ?", ids[0]).Find(&garden); result.Error != nil {
		if errors.Is(result.Error, gorm.ErrRecordNotFound) {
			return nil, nil
		}

		return nil, err
	}

	return &garden, nil
}

func (c *GardenController) Index(ctx *gin.Context) {
	gardens := make([]models.Garden, 0)
	if result := c.db.WithContext(ctx).Where("`user_id` = ?", ctx.MustGet("user").(*models.User).ID).Find(&gardens); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.HTML(http.StatusOK, "gardens", gin.H{
		"title":   "Gardens",
		"gardens": gardens,
	})
}

func (c *GardenController) Show(ctx *gin.Context) {
	garden, err := findGarden(ctx, c.hid, c.db)
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	if garden == nil {
		ctx.HTML(http.StatusNotFound, "desert", gin.H{
			"title": "Desert Found",
		})
		return
	}

	user := ctx.MustGet("user").(*models.User)
	isOwner := garden.UserID == user.ID

	query := c.db.WithContext(ctx).Preload("User").Preload("Garden").Where("`garden_id` = ?", garden.ID)
	if !isOwner {
		query = query.Where("`user_id` = ?", user.ID)
	}

	wateringRequests := make([]models.WateringRequest, 0)
	if result := query.Find(&wateringRequests); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.HTML(http.StatusOK, "gardens_details", gin.H{
		"title":            fmt.Sprintf("Garden - %s", garden.Name),
		"garden":           garden,
		"wateringRequests": wateringRequests,
		"showReports":      isOwner,
		"showCoordinates":  isOwner,
		"showInstructions": isOwner,
		"showApproves":     isOwner,
	})
}

func (c *GardenController) Create(ctx *gin.Context) {
	ctx.HTML(http.StatusOK, "gardens_create", gin.H{
		"title": "Gardens",
	})
}

func (c *GardenController) Store(ctx *gin.Context) {
	var data struct {
		Name          string  `form:"name" binding:"required"`
		Latitude      float64 `form:"latitude" binding:"required,min=-90,max=90"`
		Longitude     float64 `form:"longitude" binding:"required,min=-180,max=180"`
		WaterRequired uint    `form:"water_required" binding:"required,min=1,max=1000000"`
		Instructions  string  `form:"instructions" binding:"omitempty"`
	}
	if err := ctx.ShouldBind(&data); err != nil {
		ctx.HTML(http.StatusUnprocessableEntity, "gardens_create", gin.H{
			"title": "Gardens",
			"error": "Invalid input",
		})
		return
	}

	garden := models.Garden{
		UserID:        ctx.MustGet("user").(*models.User).ID,
		Name:          data.Name,
		Latitude:      data.Latitude,
		Longitude:     data.Longitude,
		WaterRequired: data.WaterRequired,
		Instructions:  data.Instructions,
	}
	if result := c.db.WithContext(ctx).Create(&garden); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s", garden.HashId(c.hid)))
}
