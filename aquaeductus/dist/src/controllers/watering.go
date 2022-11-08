package controllers

import (
	"database/sql"
	"errors"
	"fmt"
	"net/http"
	"time"

	"aquaeductus/models"
	"github.com/gin-gonic/gin"
	"github.com/speps/go-hashids/v2"
	"gorm.io/gorm"
)

type WateringController struct {
	db  *gorm.DB
	hid *hashids.HashID
}

func NewWateringController(db *gorm.DB, hid *hashids.HashID) *WateringController {
	return &WateringController{db: db, hid: hid}
}

func (c *WateringController) Index(ctx *gin.Context) {
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

	ctx.HTML(http.StatusOK, "gardens_watering", gin.H{
		"title":            fmt.Sprintf("Garden - %s", garden.Name),
		"user":             user,
		"garden":           garden,
		"wateringRequests": wateringRequests,
		"showReports":      isOwner,
		"showStore":        !isOwner,
		"showInstructions": isOwner,
		"showApproves":     isOwner,
	})
}

func (c *WateringController) Store(ctx *gin.Context) {
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

	if garden.UserID == user.ID {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/watering", garden.HashId(c.hid)))
		return
	}

	var data struct {
		WaterAvailable uint `form:"water_available" binding:"required,min=1,max=1000000"`
	}
	if err := ctx.ShouldBind(&data); err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/watering", garden.HashId(c.hid)))
		return
	}

	request := models.WateringRequest{
		UserID:         user.ID,
		GardenID:       garden.ID,
		WaterAvailable: data.WaterAvailable,
	}
	if result := c.db.WithContext(ctx).Create(&request); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/watering#request-%d", garden.HashId(c.hid), request.ID))
}

func (c *WateringController) Approve(ctx *gin.Context) {
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

	var params struct {
		RequestID int `uri:"rid" binding:"required"`
	}
	if err := ctx.ShouldBindUri(&params); err != nil {
		ctx.HTML(http.StatusNotFound, "desert", gin.H{
			"title": "Desert Found",
		})
		return
	}

	var request models.WateringRequest
	if result := c.db.WithContext(ctx).First(&request, params.RequestID); result.Error != nil {
		if errors.Is(result.Error, gorm.ErrRecordNotFound) {
			ctx.HTML(http.StatusNotFound, "desert", gin.H{
				"title": "Desert Found",
			})
			return
		}

		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	if garden.UserID != user.ID {
		ctx.HTML(http.StatusForbidden, "desert", gin.H{
			"title": "The Forbidden Garden",
		})
		return
	}

	request.AcceptedAt = sql.NullTime{
		Time:  time.Now(),
		Valid: true,
	}
	if result := c.db.WithContext(ctx).Save(&request); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/watering", garden.HashId(c.hid)))
}
