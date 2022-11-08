package network

import (
	"math/rand"
)

type PermutationLayer struct {
}

func (l *PermutationLayer) LayerName() string {
	return "PermutationLayer"
}

func (l *PermutationLayer) Handle(input ...float64) []float64 {
	n := make([]float64, len(input))
	copy(n, input)

	rand.Shuffle(len(n), func(i, j int) { n[i], n[j] = n[j], n[i] })

	return n
}
