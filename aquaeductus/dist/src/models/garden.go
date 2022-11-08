package models

import (
	"database/sql"
	"time"

	"github.com/speps/go-hashids/v2"
)

type Garden struct {
	ID            uint      `gorm:"primarykey"`
	UserID        uint      `gorm:"not null"`
	Name          string    `gorm:"type=varchar(255),not null"`
	Latitude      float64   `gorm:"type=double,not null"`
	Longitude     float64   `gorm:"type=double,not null"`
	WaterRequired uint      `gorm:"not null"`
	Instructions  string    `gorm:"type=text"`
	CreatedAt     time.Time `gorm:"autoCreateTime:milli;type:timestamp;not null"`
	UpdatedAt     time.Time `gorm:"autoUpdateTime:milli;type:timestamp;not null"`

	User User `gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}

func (g *Garden) HashId(hid *hashids.HashID) string {
	id, err := hid.EncodeInt64([]int64{int64(g.ID)})
	if err != nil {
		panic(err)
	}

	return id
}

type WateringRequest struct {
	ID             uint `gorm:"primarykey"`
	UserID         uint `gorm:"not null"`
	GardenID       uint `gorm:"not null"`
	WaterAvailable uint `gorm:"not null"`
	AcceptedAt     sql.NullTime
	CreatedAt      time.Time `gorm:"autoCreateTime:milli;type:timestamp;not null"`
	UpdatedAt      time.Time `gorm:"autoUpdateTime:milli;type:timestamp;not null"`

	User   User   `gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
	Garden Garden `gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}

type WeatherReport struct {
	ID        uint      `gorm:"primarykey"`
	GardenID  uint      `gorm:"not null;unique"`
	Time      time.Time `gorm:"type=date;not null"`
	Data      []byte    `gorm:"type=blob;not null"`
	CreatedAt time.Time `gorm:"autoCreateTime:milli;type:timestamp;not null"`
	UpdatedAt time.Time `gorm:"autoUpdateTime:milli;type:timestamp;not null"`

	Garden Garden `gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}
