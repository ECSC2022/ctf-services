package network

import "math/rand"

type RandomLayer struct {
}

func (l *RandomLayer) LayerName() string {
	return "RandomLayer"
}

func (l *RandomLayer) Handle(n int) []float64 {
	r := make([]float64, n)

	for i := 0; i < n; i++ {
		r[i] = rand.Float64()
	}

	return r
}
