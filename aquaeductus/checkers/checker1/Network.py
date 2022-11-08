from numpy.random import Generator

MAX_NODES = 32
MAX_NODES_BIG = 128
BIG_LAYER_PROBABILITY = 0.15
ACTIVATION_FUNCS = ['linear', 'sigmoid', 'relu', 'selu', 'softplus']


def generate_layer(rng: Generator, layer_name, node_count, extra_info=None, extra_weather_info=None):
    if layer_name == 'WeatherLayer' and extra_weather_info:
        activation = rng.choice(ACTIVATION_FUNCS + ['explu'])
    else:
        activation = rng.choice(ACTIVATION_FUNCS)
    out = [f"{layer_name} {activation}", f"{node_count}"]
    if layer_name == "InputLayer":
        inputs = rng.choice(rng.random(rng.integers(1, node_count, endpoint=True)), node_count)
        out += [f"InputNode {_in}" for _in in inputs] + ['\n']
    elif layer_name == "WeatherLayer":
        out += [f"InputNode 1" for _ in range(node_count)] + [extra_info + '\n']
    elif layer_name == "RandomLayer":
        out += [f"InputNode 1" for _ in range(node_count)] + ['\n']
    elif layer_name == "PermutationLayer":
        out += [f"InputNode 1" for _ in range(node_count)] + ['\n']
    elif layer_name == "DenseLayer":
        weights = [rng.random(extra_info) for _ in range(node_count)]
        out += [f"DenseNode {','.join([str(x) for x in weight])}" for weight in weights] + ['\n']

    return '\n'.join(out)


def generate_layer_size(rng: Generator):
    if rng.random() < BIG_LAYER_PROBABILITY:
        return rng.integers(1, MAX_NODES_BIG)
    else:
        return rng.integers(1, MAX_NODES)


def generate_network(rng: Generator, weather_layer_name=None, weather_layer_size=None, weather_layer_extra=None):
    prev_layer_size = 0
    net_definition = ""

    # How many layers (1 - 10)
    layers_count = rng.integers(1, 10, endpoint=True)

    # First layer in [weather, random, input]
    if weather_layer_name:
        layer = "WeatherLayer"
        layer_size = weather_layer_size
        net_definition += generate_layer(rng, layer, layer_size, extra_info=weather_layer_name,
                                         extra_weather_info=weather_layer_extra)
    else:
        layer = rng.choice(["RandomLayer", "InputLayer"])
        layer_size = generate_layer_size(rng)
        net_definition += generate_layer(rng, layer, layer_size)

    prev_layer_size = layer_size

    # Second -- N-1 layer in [dense, permutation]
    for _ in range(layers_count - 1):
        layer = rng.choice(["DenseLayer", "PermutationLayer"])
        layer_size = generate_layer_size(rng)
        if layer == "DenseLayer":
            net_definition += generate_layer(rng, layer, layer_size, prev_layer_size)
            prev_layer_size = layer_size
        else:
            net_definition += generate_layer(rng, layer, prev_layer_size)

    return net_definition, prev_layer_size
