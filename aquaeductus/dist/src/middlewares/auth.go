package middlewares

import (
	"errors"
	"net/http"

	"aquaeductus/models"
	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func Auth(db *gorm.DB) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		session := sessions.Default(ctx)
		userIdI := session.Get("user_id")
		if userIdI == nil {
			ctx.Abort()
			ctx.Redirect(http.StatusFound, "/login")
			return
		}
		userId := userIdI.(uint)

		var user models.User
		if result := db.WithContext(ctx).First(&user, userId); result.Error != nil {
			if errors.Is(result.Error, gorm.ErrRecordNotFound) {
				ctx.Abort()
				ctx.Redirect(http.StatusFound, "/login")
				return
			}

			_ = ctx.AbortWithError(http.StatusInternalServerError, result.Error)
			return
		}

		ctx.Set("user", &user)

		ctx.Next()
	}
}
