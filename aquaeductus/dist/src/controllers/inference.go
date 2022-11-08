package controllers

import (
	"bytes"
	"compress/gzip"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"

	"aquaeductus/network"
	"github.com/gin-gonic/gin"
	"github.com/speps/go-hashids/v2"
	"gorm.io/gorm"
)

type InferenceController struct {
	db  *gorm.DB
	hid *hashids.HashID
}

func NewInferenceController(db *gorm.DB, hid *hashids.HashID) *InferenceController {
	return &InferenceController{db: db, hid: hid}
}

func (c *InferenceController) Run(ctx *gin.Context) {
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

	fileHeader, err := ctx.FormFile("network")
	if err != nil || fileHeader.Size > 512*1024 {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s", garden.HashId(c.hid)))
		return
	}

	file, err := fileHeader.Open()
	if err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s", garden.HashId(c.hid)))
		return
	}

	contentCompressed, err := io.ReadAll(file)
	if err != nil {
		ctx.Redirect(http.StatusFound, fmt.Sprintf("/gardens/%s", garden.HashId(c.hid)))
		return
	}

	networkReader, err := gzip.NewReader(bytes.NewReader(contentCompressed))
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	defer networkReader.Close()
	content, err := io.ReadAll(networkReader)
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	module, err := network.NewWasmModule(c.db, garden)
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	defer module.Close()

	result, err := module.NetworkCompute(string(content))
	if err != nil {
		result = "null"
	}

	buffer := bytes.Buffer{}
	gz, err := gzip.NewWriterLevel(&buffer, gzip.DefaultCompression)
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	if _, err := gz.Write(module.Stdout.Bytes()); err != nil {
		_ = gz.Close()
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	_ = gz.Close()

	stdout := base64.RawURLEncoding.EncodeToString(buffer.Bytes())

	ctx.Header("Content-Type", "application/json")
	ctx.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"inference-%d.json\"", garden.ID))
	ctx.String(http.StatusOK, fmt.Sprintf("{\"stdout\":\"%s\",\"result\":%s}", stdout, result))
}
