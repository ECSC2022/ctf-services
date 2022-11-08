package models

import (
	"time"
)

type User struct {
	ID        uint      `gorm:"primarykey"`
	Username  string    `gorm:"type:varchar(255);not null;unique"`
	Password  []byte    `gorm:"type:varbinary(255);not null"`
	CreatedAt time.Time `gorm:"autoCreateTime:milli;type:timestamp;not null"`
	UpdatedAt time.Time `gorm:"autoUpdateTime:milli;type:timestamp;not null"`
}
