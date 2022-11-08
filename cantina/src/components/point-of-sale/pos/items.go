package pos

import (
	"bufio"
	"errors"
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type OrderItem struct {
	Name     string `json:"name" yaml:"name"`
	ItemId   uint32 `json:"item_id" yaml:"item_id"`
	Price    uint32 `json:"price" yaml:"price"`
	ImageUrl string `json:"image_url" yaml:"image_url"`
}

type OrderCategory struct {
	Name  string      `json:"name" yaml:"name"`
	Items []OrderItem `json:"items" yaml:"items"`
}

type ItemOverview struct {
	Cats     []OrderCategory   `json:"categories" yaml:"categories"`
	PriceMap map[uint32]uint32 `json:"-" yaml:"-"`
}

func LoadItems() (items *ItemOverview, err error) {
	configPath, ok := os.LookupEnv("ITEM_CONFIG")
	if !ok {
		err = errors.New("No ITEM_CONFIG path provided")
		return
	}

	f, err := os.Open(configPath)
	if err != nil {
		err = fmt.Errorf("Couldn't open item config: %w", err)
		return
	}
	defer f.Close()

	// Parse the items we have defined in the yaml
	r := bufio.NewReader(f)
	decoder := yaml.NewDecoder(r)
	items = new(ItemOverview)
	if err = decoder.Decode(items); err != nil {
		err = fmt.Errorf("Error parsing item config: %w", err)
		return
	}

	// Calculate the price map out of the items
	items.PriceMap = make(map[uint32]uint32)
	for _, categories := range items.Cats {
		for _, item := range categories.Items {
			items.PriceMap[item.ItemId] = item.Price
		}
	}

	return
}
