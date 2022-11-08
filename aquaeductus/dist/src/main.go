package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"flag"
	"fmt"
	"html/template"
	"os"
	"time"

	"aquaeductus/controllers"
	"aquaeductus/middlewares"
	"aquaeductus/models"
	"aquaeductus/network"
	"github.com/gin-contrib/gzip"
	limits "github.com/gin-contrib/size"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/speps/go-hashids/v2"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var (
	port = flag.Int("port", 8080, "The server port")

	dbMaxOpenConn = flag.Int("db_max_conn", 32, "Maximum number of open connections with the database")
	dbMaxIdleConn = flag.Int("db_idle_conn", 8, "Maximum number of idle connections with the database")

	wasmPath = flag.String("wasm-module", "release.wasm", "Path to wasm module")
)

var (
	Gorm    *gorm.DB
	HashIds *hashids.HashID
)

var (
	sessionAuthenticationKey []byte
	sessionEncryptionKey     []byte
	hashidsSalt              []byte
)

func main() {
	time.Local = time.UTC
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs

	flag.Parse()

	initDatabase()
	initSecrets()

	hd, err := hashids.NewWithData(&hashids.HashIDData{
		Alphabet:  hashids.DefaultAlphabet,
		MinLength: 8,
		Salt:      hex.EncodeToString(hashidsSalt),
	})
	if err != nil {
		log.Fatal().
			Err(err).
			Msg("HashIds init failed")
		return
	}
	HashIds = hd

	network.LoadWasm(*wasmPath)

	go cleanup()
	run()
}

func initDatabase() {
	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local&checkConnLiveness=True",
		os.Getenv("DATABASE_USERNAME"),
		os.Getenv("DATABASE_PASSWORD"),
		"aquaeductus-database",
		3306,
		os.Getenv("DATABASE_DBNAME"),
	)
	var err error
	Gorm, err = gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: logger.New(
			&log.Logger,
			logger.Config{
				SlowThreshold:             10 * time.Second,
				LogLevel:                  logger.Error,
				IgnoreRecordNotFoundError: true,
				Colorful:                  false,
			},
		),
	})
	if err != nil {
		log.Fatal().
			Err(err).
			Msg("Database connection failed")
		return
	}

	Gorm.Logger.LogMode(logger.Silent)

	db, err := Gorm.DB()
	if err != nil {
		log.Fatal().
			Err(err).
			Msg("Database connection failed")
		return
	}
	db.SetMaxOpenConns(*dbMaxOpenConn)
	db.SetMaxIdleConns(*dbMaxIdleConn)
	db.SetConnMaxLifetime(time.Hour)

	if err := db.Ping(); err != nil {
		log.Fatal().
			Err(err).
			Msg("Failed to ping database")
	}

	if err := Gorm.AutoMigrate(
		&models.Config{},
		&models.User{},
		&models.Garden{},
		&models.WateringRequest{},
		&models.WeatherReport{},
	); err != nil {
		log.Fatal().
			Err(err).
			Msg("Failed to migrate database")
	}
}

func initSecrets() {
	randomBytesInit := func(size int) func() []byte {
		return func() []byte {
			t := make([]byte, size)
			if _, err := rand.Read(t); err != nil {
				panic(err)
			}
			return t
		}
	}

	sessionAuthenticationKey = secretGetOrInit("session_authentication_key", randomBytesInit(32))
	sessionEncryptionKey = secretGetOrInit("session_encryption_key", randomBytesInit(32))
	hashidsSalt = secretGetOrInit("hashids_salt", randomBytesInit(16))
}

func cleanup() {
	for {
		log.Info().Msg("cleanup")

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)

		result := Gorm.WithContext(ctx).Where("`created_at` < ?", time.Now().Add(-30*time.Minute)).Delete(&models.User{})
		if result.Error != nil {
			log.Error().Err(result.Error).Msg("cleanup failed")
		} else {
			log.Info().Int64("records_deleted", result.RowsAffected).Msg("cleanup completed")
		}

		cancel()
		time.Sleep(5 * time.Minute)
	}
}

func run() {
	gin.SetMode(gin.ReleaseMode)

	app := gin.New()

	app.SetFuncMap(template.FuncMap{
		"hashid": func(id uint) string {
			sid, err := HashIds.EncodeInt64([]int64{int64(id)})
			if err != nil {
				panic(err)
			}

			return sid
		},
		"dateformat": func(t time.Time, format string) string {
			return t.Format(format)
		},
	})
	app.LoadHTMLGlob("views/*")

	app.Use(gin.Logger())
	app.Use(middlewares.ErrorLogging())
	app.Use(gin.Recovery())
	app.Use(gzip.Gzip(gzip.DefaultCompression))
	app.Use(limits.RequestSizeLimiter(5 * 1024 * 1024))
	app.Use(middlewares.Session(sessionAuthenticationKey, sessionEncryptionKey))

	app.Static("/assets", "/app/assets")

	{
		auth := controllers.NewAuthController(Gorm)
		app.GET("/login", auth.Index)
		app.POST("/login", auth.Login)
		app.POST("/register", auth.Register)
	}

	{
		r := app.Group("/", middlewares.Auth(Gorm))

		index := controllers.NewIndexController(Gorm)
		r.GET("/", index.Index)

		gardens := controllers.NewGardenController(Gorm, HashIds)
		r.GET("/gardens", gardens.Index)
		r.GET("/gardens/create", gardens.Create)
		r.POST("/gardens", gardens.Store)
		r.GET("/gardens/:id", gardens.Show)

		watering := controllers.NewWateringController(Gorm, HashIds)
		r.GET("/gardens/:id/watering", watering.Index)
		r.POST("/gardens/:id/watering", watering.Store)
		r.POST("/gardens/:id/watering/:rid", watering.Approve)

		weather := controllers.NewWeatherController(Gorm, HashIds)
		r.GET("/gardens/:id/reports", weather.Show)
		r.GET("/gardens/:id/reports/download", weather.Download)
		r.POST("/gardens/:id/reports", weather.Store)

		inference := controllers.NewInferenceController(Gorm, HashIds)
		r.POST("/gardens/:id/infer", inference.Run)
	}

	if err := app.Run(fmt.Sprintf(":%d", *port)); err != nil {
		log.Fatal().Err(err).Msg("Failed to start server")
	}
}
