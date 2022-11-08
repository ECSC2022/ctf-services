package middlewares

import (
	"net/http"

	"github.com/gin-contrib/sessions"
	"github.com/gin-contrib/sessions/cookie"
	"github.com/gin-gonic/gin"
)

func Session(authKey, encryptKey []byte) gin.HandlerFunc {
	store := cookie.NewStore(authKey, encryptKey)

	store.Options(sessions.Options{
		MaxAge:   24 * 60 * 60,
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
	})

	return sessions.Sessions("session", store)
}
