package main

import (
	"errors"

	"aquaeductus/models"
	"gorm.io/gorm"
)

func secretGetOrInit(key string, initializer func() []byte) []byte {
	var config models.Config
	if result := Gorm.Where("`key` = ?", key).First(&config); result.Error != nil {
		if !errors.Is(result.Error, gorm.ErrRecordNotFound) {
			panic(result.Error)
		}

		config.Key = key
		config.Value = initializer()

		if result := Gorm.Create(&config); result.Error != nil {
			panic(result.Error)
		}
	}

	return config.Value
}
