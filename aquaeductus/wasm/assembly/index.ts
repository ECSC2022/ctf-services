import {RegExp} from 'assemblyscript-regex/assembly/regexp';
import * as rpc from './rpc';

function hex_encode(input: string): string {
    return input.split("")
        .map<string>((c: string) => c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("");
}

function hex_decode(input: string): ArrayBuffer {
    const buffer = new ArrayBuffer((1 + (((input.length) - 1) / 8)) * 8); // Align to 64bit
    const view = new DataView(buffer);
    for (let n = 0; n < input.length; n += 2) {
        view.setInt8(n / 2, i8.parse(input.substr(n, 2), 16));
    }
    return buffer;
}

function arrayBufferToString(buffer: ArrayBuffer): string {
    const byteArray = Uint8Array.wrap(buffer);
    let str = "", cc = 0, numBytes = 0;
    for (let i = 0, len = byteArray.length; i < len; ++i) {
        const v = byteArray[i];
        if (numBytes > 0) {
            //2 bit determining that this is a tailing byte + 6 bit of payload
            if ((cc & 192) === 192) {
                //processing tailing-bytes
                cc = (cc << 6) | (v & 63);
            } else {
                throw new Error("this is no tailing-byte");
            }
        } else if (v < 128) {
            //single-byte
            numBytes = 1;
            cc = v;
        } else if (v < 192) {
            //these are tailing-bytes
            throw new Error("invalid byte, this is a tailing-byte")
        } else if (v < 224) {
            //3 bits of header + 5bits of payload
            numBytes = 2;
            cc = v & 31;
        } else if (v < 240) {
            //4 bits of header + 4bit of payload
            numBytes = 3;
            cc = v & 15;
        } else {
            //UTF-8 theoretically supports up to 8 bytes containing up to 42bit of payload
            //but JS can only handle 16bit.
            throw new Error("invalid encoding, value out of range")
        }
        if (--numBytes === 0) {
            str += String.fromCharCode(cc);
        }
    }
    if (numBytes) {
        throw new Error("the bytes don't sum up");
    }
    return str;
}

const floatRegex = new RegExp("^[0-9]+(\\.[0-9]+)?$");

function ParseFloat(input: string): f64 {
    input = input.trim()
    if (!floatRegex.test(input)) {
        console.log(input + " is not a float");
        return 0;
    }

    return parseFloat(input);
}

class Network {
    layers: Array<Layer>;

    constructor(layers: Array<Layer>) {
        this.layers = layers;
    }
}

class Node {
    ins: Array<Node>;
    weights: Array<f64>;
    value: f64;
    activation: (v: f64) => f64;

    constructor(ins: Array<Node>, weights: Array<f64>, activation: string) {
        if (ins.length != weights.length) {
            throw new Error('input nodes and weights length mismatch');
        }
        this.ins = ins;
        this.weights = weights;
        this.value = NaN;

        if (!activation_map.has(activation)) {
            throw new Error('Unknown activation function');
        }
        this.activation = activation_map.get(activation);
    }

    prepare(parent: string): void {
    }

    getValue(): f64 {
        if (isNaN(this.value)) {
            this.compute();
        }
        return this.value;
    }

    compute(): void {
        assert(false);
    }
}

class InputNode extends Node {
    constructor(value: f64, activation: string) {
        super(new Array<Node>(0), new Array<f64>(0), activation);
        this.value = this.activation(value);
    }

    compute(): void {
    }
}

class DenseNode extends Node {
    constructor(ins: Array<Node>, weights: Array<f64>, activation: string) {
        super(ins, weights, activation);
    }

    compute(): void {
        assert(this.ins.length === this.weights.length);
        this.value = 0;
        for (let i = 0; i < this.ins.length; ++i) {
            this.value += this.ins[i].getValue() * this.weights[i];
        }
        this.value = this.activation(this.value);
    }
}

class RetrievalNode extends Node {
    target: string;

    constructor(target: string, activation: string) {
        super(new Array<Node>(0), new Array<f64>(0), activation);
        this.target = target;
    }

    prepare(parent: string): void {
        let data = rpc.retrieve(1, parent + "." + this.target).substr(6);
        this.value = ParseFloat(data);
    }

    compute(): void {
        this.value = this.activation(this.value);
    }
}

class Layer {
    nodes: Array<Node>;

    constructor(nodes: Array<Node>) {
        this.nodes = nodes;
    }

    compute(): void {
    }

    getValue(): Array<f64> {
        let result: Array<f64> = [];
        for (let i = 0; i < this.nodes.length; i++) {
            result.push(this.nodes[i].getValue());
        }
        return result;
    }
}

class DenseLayer extends Layer {
    constructor(nodes: Array<Node>) {
        super(nodes);
    }

    compute(): void {
        for (let i = 0; i < this.nodes.length; ++i) {
            this.nodes[i].compute();
        }
    }
}

class InputLayer extends Layer {
    constructor(nodes: Array<Node>) {
        super(nodes);
    }

    compute(): void {
    }
}

class CustomLayerToGo extends Layer {
    parameters: string = '';

    go_handler: i64;
    go_result: string = '';

    constructor(nodes: Array<Node>, layer_package: string, layer_type: string, parameters: string = "") {
        super(nodes);
        this.parameters = parameters.trimEnd()

        this.go_handler = rpc.instantiate(layer_package, layer_type);
        if (this.go_handler == 0) {
            throw new Error('Invalid handler');
        }
    }

    compute(): void {
        this.go_result = rpc.invoke(this.go_handler, "Handle", this.parameters)
        if (this.go_result.startsWith("error ")) {
            throw new Error(this.go_result.substr(6))
        }
    }
}

class PermutationLayer extends CustomLayerToGo {
    constructor(nodes: Array<Node>) {
        super(
            nodes,
            "aquaeductus/network",
            'PermutationLayer',
            nodes.map<string>((node: Node): string => "float " + node.getValue().toString()).join(" ")
        );
    }

    compute(): void {
        super.compute();
        let parsed_result = this.go_result.substr(7, this.go_result.length - 2).replaceAll("float ", "").split(' ');
        for (let i = 0; i < this.nodes.length; ++i) {
            this.nodes[i].value = ParseFloat(parsed_result[i]);
        }
    }
}

class RandomLayer extends CustomLayerToGo {
    constructor(nodes: Array<Node>) {
        super(nodes, "aquaeductus/network", 'RandomLayer', "int " + nodes.length.toString());
    }

    compute(): void {
        super.compute();
        let parsed_result = this.go_result.substr(7, this.go_result.length - 2).replaceAll("float ", "").split(' ');
        for (let i = 0; i < this.nodes.length; ++i) {
            this.nodes[i].value = ParseFloat(parsed_result[i]);
        }
    }
}

class WeatherLayer extends Layer {
    report_name: string = '';
    elu: boolean = false;

    constructor(nodes: Array<Node>, report_name: string, elu: boolean) {
        super(nodes);
        this.report_name = report_name;
        this.elu = elu;
    }

    compute(): void {
        super.compute();
        let data = hex_decode(rpc.retrieve(1, this.report_name).substr(7));
        let view = new DataView(data);
        let offset = 0;
        const le = true;

        // Skip first line
        if (this.elu) {
            // Read N floats on first line
            const first: Array<f64> = [];
            for (let i = 0; i < this.nodes.length; ++i) {
                first[i] = (offset < data.byteLength - 8) ? view.getFloat64(offset, le) : 0;
                offset += 8;
            }

            // Read until a new line
            let foundNewLine = false;
            while (offset < data.byteLength) {
                const char = view.getInt8(offset);
                offset++;

                if (char == 0xA) {
                    foundNewLine = true;
                    break;
                }
            }
            if (!foundNewLine) {
                for (let i = 0; i < this.nodes.length; ++i) this.nodes[i].value = 0;
                return;
            }

            // Read N floats on second line
            const second: Array<f64> = [];
            for (let i = 0; i < this.nodes.length; ++i) {
                second[i] = (offset < data.byteLength - 8) ? view.getFloat64(offset, le) : 0;
                offset += 8;
            }

            // Put lines together
            for (let i = 0; i < this.nodes.length; ++i) {
                this.nodes[i].value = explu(first[i], second[i]);
            }
        } else {
            // Read N floats
            for (let i = 0; i < this.nodes.length; ++i) {
                this.nodes[i].value = (offset < data.byteLength - 8) ? view.getFloat64(offset, le) : 0;
                offset += 8;
            }
        }
    }
}

class LocationLayer extends Layer {
    constructor(nodes: Array<Node>) {
        super(nodes);
    }

    compute(): void {
        super.compute();

        for (let i = 0; i < this.nodes.length; ++i) {
            this.nodes[i].prepare("Garden");
        }
    }
}


let MAX_LINES: i32 = 1300;

function parse_network(raw: string): Network {
    let layers: Array<Layer> = [];
    let input: Array<string> = raw.split('\n');
    console.log(`found ${input.length} lines in NN definition`);
    let line_count: i32 = 0;
    if (line_count > MAX_LINES) {
        throw new Error('Network too big - too many lines in file');
    }
    while (line_count < input.length - 1) {
        console.log(`parsing from line ${line_count}`);

        // first line: layer_type activation_function
        let first_line = input[line_count].split(' ');
        let layer_type: string = first_line[0];
        let activation_function = first_line[1];

        // second line: how many nodes in the layer
        let node_count: i32 = <i32>parseInt(input[line_count + 1]);
        if (node_count > 128) {
            throw new Error('Max 128 nodes per layer');
        }
        let nodes: Array<Node> = [];

        console.log(`found layer ${layer_type} with ${node_count} nodes`);

        // third line -- n.nodes+3 line: one line per node
        for (let node_idx = 0; node_idx < node_count; ++node_idx) {
            let node_line_idx = line_count + 2 + node_idx;
            let node_line: Array<string> = input[node_line_idx].split(' ');
            if (node_line.length != 2)
                throw new Error(`Node description should follow the format NODE_TYPE VALUE(S)`);

            // node type
            let node_type: string = node_line[0];

            console.log(`line ${node_line_idx} declares ${node_type}`);

            let new_node: Node;
            if (node_type == 'InputNode') {
                new_node = new InputNode(ParseFloat(node_line[1]), activation_function);
            } else if (node_type == 'DenseNode') {
                let weights: Array<f64> = [];
                let weights_to_parse: Array<string> = node_line[1].split(',');
                for (
                    let weight_idx = 0;
                    weight_idx < weights_to_parse.length;
                    ++weight_idx
                ) {
                    weights.push(ParseFloat(weights_to_parse[weight_idx]));
                }
                new_node = new DenseNode(
                    layers[layers.length - 1].nodes,
                    weights,
                    activation_function
                );
            } else if (node_type == 'RetrievalNode') {
                new_node = new RetrievalNode(node_line[1], activation_function)
            } else throw new Error('Unknown node type');
            nodes.push(new_node);
        }

        // extra info, can be empty
        let extra_info: string = input[line_count + 2 + node_count];

        // layer_type + num_nodes + #nodes + extra_info
        line_count += 1 + 1 + nodes.length + 1;

        let new_layer: Layer;
        if (layer_type == 'InputLayer')
            new_layer = new InputLayer(nodes);
        else if (layer_type == 'DenseLayer')
            new_layer = new DenseLayer(nodes);
        else if (layer_type == 'PermutationLayer') {
            for (let i = 0; i < nodes.length; ++i)
                nodes[i].value = layers[layers.length - 1].nodes[i].getValue();
            new_layer = new PermutationLayer(nodes);
        } else if (layer_type == 'RandomLayer')
            new_layer = new RandomLayer(nodes);
        else if (layer_type == 'WeatherLayer')
            new_layer = new WeatherLayer(nodes, extra_info, activation_function == 'explu');
        else if (layer_type == 'LocationLayer')
            new_layer = new LocationLayer(nodes);
        else throw new Error('Unknown layer type');

        layers.push(new_layer);
        new_layer.compute();
    }

    return new Network(layers);
}

// activation functions

var activation_map = new Map<string, (v: f64) => f64>();

function linear(input: f64): f64 {
    return input;
}

activation_map.set('linear', linear);

function sigmoid(input: f64): f64 {
    return 1 / (1 + Math.exp(-input));
}

activation_map.set('sigmoid', sigmoid);

function relu(input: f64): f64 {
    return Math.max(0, input);
}

activation_map.set('relu', relu);

function elu(input: f64, parameter: f64): f64 {
    return input > 0 ? input : parameter * Math.expm1(input);
}

function explu(input: f64, parameter: f64): f64 {
    return parameter * Math.expm1(input);
}

activation_map.set('explu', linear);

function selu(input: f64): f64 {
    return 1.0507 * elu(input, 1.67326);
}

activation_map.set('selu', selu);

function softplus(input: f64): f64 {
    return Math.log(1 + Math.exp(input));
}

activation_map.set('softplus', softplus);


export function compute_network(definition: string): string {
    let net = parse_network(definition);

    // compute_network must return json, print in the response as-is
    return (
        '[' +
        net.layers[net.layers.length - 1]
            .getValue()
            .map((f: f64): string => f.toString())
            .join(',') +
        ']'
    );
}
