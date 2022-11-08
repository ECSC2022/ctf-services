package models

type Config struct {
	Key   string `gorm:"type:varchar(255);primarykey"`
	Value []byte `gorm:"type:varbinary(255);not null"`
}
