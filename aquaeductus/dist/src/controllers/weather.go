package controllers

import (
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"aquaeductus/models"
	"github.com/gin-gonic/gin"
	"github.com/speps/go-hashids/v2"
	"gorm.io/gorm"
)

type WeatherController struct {
	db  *gorm.DB
	hid *hashids.HashID
}

func NewWeatherController(db *gorm.DB, hid *hashids.HashID) *WeatherController {
	return &WeatherController{db: db, hid: hid}
}

func (c *WeatherController) Show(ctx *gin.Context) {
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

	if !isOwner {
		ctx.HTML(http.StatusForbidden, "desert", gin.H{
			"title": "The Forbidden Garden",
		})
		return
	}

	var report models.WeatherReport
	if result := c.db.WithContext(ctx).Where("`garden_id` = ?", garden.ID).First(&report); result.Error != nil {
		if !errors.Is(result.Error, gorm.ErrRecordNotFound) {
			_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
			return
		}
	}

	ctx.HTML(http.StatusOK, "gardens_weather", gin.H{
		"title":   fmt.Sprintf("Garden - %s", garden.Name),
		"garden":  garden,
		"report":  report,
		"isOwner": isOwner,
	})
}

func (c *WeatherController) Download(ctx *gin.Context) {
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

	if !isOwner {
		ctx.HTML(http.StatusForbidden, "desert", gin.H{
			"title": "The Forbidden Garden",
		})
		return
	}

	var report models.WeatherReport
	if result := c.db.WithContext(ctx).Where("`garden_id` = ?", garden.ID).First(&report); result.Error != nil {
		if errors.Is(result.Error, gorm.ErrRecordNotFound) {
			ctx.HTML(http.StatusNotFound, "desert", gin.H{
				"title": "Desert Found",
			})
			return
		}

		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"report-%d.bin\"", garden.ID))
	ctx.Data(http.StatusOK, "application/octet-stream", report.Data)
}

func (c *WeatherController) Store(ctx *gin.Context) {
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

	if garden.UserID != user.ID {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	var data struct {
		Time string `form:"date" binding:"required,datetime=2006-01-02"`
	}
	if err := ctx.ShouldBind(&data); err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	t, err := time.Parse("2006-01-02", data.Time)
	if err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	fileHeader, err := ctx.FormFile("report")
	if err != nil || fileHeader.Size > 512*1024 {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	file, err := fileHeader.Open()
	if err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	content, err := io.ReadAll(file)
	if err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
		return
	}

	report := models.WeatherReport{
		GardenID: garden.ID,
		Time:     t,
		Data:     content,
	}
	if result := c.db.WithContext(ctx).Create(&report); result.Error != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s/reports", garden.HashId(c.hid)))
}
