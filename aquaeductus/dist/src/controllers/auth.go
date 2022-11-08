package controllers

import (
	"errors"
	"net/http"

	"aquaeductus/models"
	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"github.com/go-sql-driver/mysql"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type AuthController struct {
	db *gorm.DB
}

func NewAuthController(db *gorm.DB) *AuthController {
	return &AuthController{db: db}
}

type authBody struct {
	Username string `json:"username" form:"username" binding:"required,min=1,max=255"`
	Password string `json:"password" form:"password" binding:"required,min=1,max=255"`
}

func (c *AuthController) Index(ctx *gin.Context) {
	ctx.HTML(http.StatusOK, "auth", gin.H{
		"title": "Auth",
	})
}

func (c *AuthController) Login(ctx *gin.Context) {
	var body authBody
	if err := ctx.ShouldBind(&body); err != nil {
		ctx.HTML(http.StatusUnprocessableEntity, "auth.html", gin.H{
			"title": "Auth",
			"error": "Invalid input",
		})
		return
	}

	var user models.User
	if result := c.db.WithContext(ctx).Where("username = ?", body.Username).First(&user); result.Error != nil {
		if errors.Is(result.Error, gorm.ErrRecordNotFound) {
			ctx.HTML(http.StatusUnprocessableEntity, "auth", gin.H{
				"title": "Auth",
				"error": "Invalid credentials",
			})
			return
		}

		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	if err := bcrypt.CompareHashAndPassword(user.Password, []byte(body.Password)); err != nil {
		if errors.Is(err, bcrypt.ErrMismatchedHashAndPassword) {
			ctx.HTML(http.StatusUnprocessableEntity, "auth", gin.H{
				"title": "Auth",
				"error": "Invalid credentials",
			})
			return
		}

		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	session := sessions.Default(ctx)
	session.Set("user_id", user.ID)
	if err := session.Save(); err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	ctx.Redirect(http.StatusFound, "/")
}

func (c *AuthController) Register(ctx *gin.Context) {
	var body authBody
	if err := ctx.ShouldBind(&body); err != nil {
		ctx.HTML(http.StatusUnprocessableEntity, "auth", gin.H{
			"title": "Auth",
			"error": "Invalid input",
		})
		return
	}

	password, err := bcrypt.GenerateFromPassword([]byte(body.Password), bcrypt.DefaultCost)
	if err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	user := models.User{
		Username: body.Username,
		Password: password,
	}
	if result := c.db.WithContext(ctx).Create(&user); result.Error != nil {
		var mysqlErr *mysql.MySQLError
		if errors.As(result.Error, &mysqlErr) && mysqlErr.Number == 1062 {
			ctx.HTML(http.StatusConflict, "auth", gin.H{
				"title": "Auth",
				"error": "User already registered",
			})
			return
		}

		_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
		return
	}

	session := sessions.Default(ctx)
	session.Set("user_id", user.ID)
	if err := session.Save(); err != nil {
		_ = ctx.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	ctx.Redirect(http.StatusFound, "/")
}
