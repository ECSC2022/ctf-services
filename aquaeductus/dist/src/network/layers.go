package network

var layers = []Layer{
	&PermutationLayer{},
	&RandomLayer{},
}

type Layer interface {
	LayerName() string
}
