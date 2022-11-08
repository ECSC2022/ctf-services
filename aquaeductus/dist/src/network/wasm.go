package network

import (
	"bytes"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"unicode/utf16"

	"aquaeductus/models"
	"github.com/modern-go/reflect2"
	"github.com/rs/zerolog/log"
	"github.com/wasmerio/wasmer-go/wasmer"
	"gorm.io/gorm"
)

var (
	wasmModule []byte
)

func LoadWasm(path string) {
	f, err := os.Open(path)
	if err != nil {
		panic(err)
	}

	data, err := io.ReadAll(f)
	if err != nil {
		panic(err)
	}

	wasmModule = data

	log.Info().Int("layers_count", len(layers)).Msg("wasm.loaded")
}

type wasmError struct {
	message      string
	filename     string
	lineNumber   uint32
	columnNumber uint32
}

func (w *wasmError) Error() string {
	return fmt.Sprintf("%s in %s:%d:%d", w.message, w.filename, w.lineNumber, w.columnNumber)
}

type WasmModule struct {
	engine   *wasmer.Engine
	store    *wasmer.Store
	instance *wasmer.Instance

	handles   sync.Map
	handleIdx uintptr

	Stdout bytes.Buffer

	Garden     *models.Garden
	ReportData string
}

func NewWasmModule(db *gorm.DB, garden *models.Garden) (*WasmModule, error) {
	m := WasmModule{}

	m.Garden = garden

	var report models.WeatherReport
	if result := db.Where("`garden_id` = ?", garden.ID).First(&report); result.Error != nil {
		if !errors.Is(result.Error, gorm.ErrRecordNotFound) {
			return nil, result.Error
		}
	} else {
		m.ReportData = string(report.Data)
	}

	m.engine = wasmer.NewEngine()
	m.store = wasmer.NewStore(m.engine)

	module, err := wasmer.NewModule(m.store, wasmModule)
	if err != nil {
		return nil, err
	}

	importObject := wasmer.NewImportObject()

	m.registerHandle(&m)

	importObject.Register("env", map[string]wasmer.IntoExtern{
		"abort": wasmer.NewFunction(
			m.store,
			wasmer.NewFunctionType(wasmer.NewValueTypes(wasmer.I32, wasmer.I32, wasmer.I32, wasmer.I32), wasmer.NewValueTypes()),
			m.abort,
		),
		"console.log": wasmer.NewFunction(
			m.store,
			wasmer.NewFunctionType(wasmer.NewValueTypes(wasmer.I32), wasmer.NewValueTypes()),
			m.log,
		),
	})
	importObject.Register("rpc", map[string]wasmer.IntoExtern{
		"instantiate": wasmer.NewFunction(
			m.store,
			wasmer.NewFunctionType(wasmer.NewValueTypes(wasmer.I32, wasmer.I32), wasmer.NewValueTypes(wasmer.I64)),
			m.rpcInstantiate,
		),
		"invoke": wasmer.NewFunction(
			m.store,
			wasmer.NewFunctionType(wasmer.NewValueTypes(wasmer.I64, wasmer.I32, wasmer.I32), wasmer.NewValueTypes(wasmer.I32)),
			m.rpcInvoke,
		),
		"retrieve": wasmer.NewFunction(
			m.store,
			wasmer.NewFunctionType(wasmer.NewValueTypes(wasmer.I64, wasmer.I32), wasmer.NewValueTypes(wasmer.I32)),
			m.rpcRetrieve,
		),
	})

	m.instance, err = wasmer.NewInstance(module, importObject)
	if err != nil {
		return nil, err
	}

	return &m, nil
}

func (m *WasmModule) registerHandle(value any) uintptr {
	h := atomic.AddUintptr(&m.handleIdx, 1)
	m.handles.Store(h, value)
	return h
}

func (m *WasmModule) abort(args []wasmer.Value) ([]wasmer.Value, error) {
	if len(args) < 4 {
		return nil, errors.New("invalid args number")
	}

	var err error

	messagePointer := uint32(args[0].I32())
	message := ""
	if messagePointer != 0 {
		message, err = m.getString(messagePointer)
		if err != nil {
			return nil, err
		}
	}

	filenamePointer := uint32(args[1].I32())
	filename := ""
	if filenamePointer != 0 {
		filename, err = m.getString(filenamePointer)
		if err != nil {
			return nil, err
		}
	}

	lineNumber := args[2].I32()
	columnNumber := args[3].I32()

	wasmErr := wasmError{
		message:      message,
		filename:     filename,
		lineNumber:   uint32(lineNumber),
		columnNumber: uint32(columnNumber),
	}

	if _, err := m.Stdout.WriteString(wasmErr.Error() + "\n"); err != nil {
		return nil, err
	}

	return nil, &wasmErr
}

func (m *WasmModule) log(args []wasmer.Value) ([]wasmer.Value, error) {
	if len(args) < 1 {
		return nil, errors.New("invalid args number")
	}

	s, err := m.getString(uint32(args[0].I32()))
	if err != nil {
		return nil, err
	}

	if _, err := m.Stdout.WriteString(s + "\n"); err != nil {
		return nil, err
	}

	return []wasmer.Value{}, nil
}

func (m *WasmModule) rpcInstantiate(args []wasmer.Value) ([]wasmer.Value, error) {
	if len(args) < 2 {
		return nil, errors.New("invalid args number")
	}

	p, err := m.getString(uint32(args[0].I32()))
	if err != nil {
		return nil, err
	}

	n, err := m.getString(uint32(args[1].I32()))
	if err != nil {
		return nil, err
	}

	t := reflect2.TypeByPackageName(p, n)
	if t == nil {
		return nil, errors.New("unknown type")
	}

	v := t.New()

	h := m.registerHandle(v)

	return []wasmer.Value{wasmer.NewI64(uint(h))}, nil
}

func (m *WasmModule) rpcInvoke(args []wasmer.Value) ([]wasmer.Value, error) {
	if len(args) < 3 {
		return nil, errors.New("invalid args number")
	}

	h := uintptr(args[0].I64())
	v, ok := m.handles.Load(h)
	if !ok {
		return nil, errors.New("handle lost")
	}

	meth, err := m.getString(uint32(args[1].I32()))
	if err != nil {
		return nil, err
	}

	par, err := m.getString(uint32(args[2].I32()))
	if err != nil {
		return nil, err
	}

	parameters, err := m.parseParameters(par)
	if err != nil {
		return nil, err
	}

	method := reflect.ValueOf(v).MethodByName(meth)
	methodType := method.Type()
	var result []reflect.Value
	if methodType.IsVariadic() {
		varType := methodType.In(methodType.NumIn() - 1).Elem()
		switch varType.Kind() {
		case reflect.Int:
			input := make([]int, len(parameters))
			for i := 0; i < len(parameters); i++ {
				input[i] = int(parameters[i].Int())
			}
			result = method.CallSlice([]reflect.Value{reflect.ValueOf(input)})
		case reflect.Float64:
			input := make([]float64, len(parameters))
			for i := 0; i < len(parameters); i++ {
				input[i] = parameters[i].Float()
			}
			result = method.CallSlice([]reflect.Value{reflect.ValueOf(input)})
		default:
			return nil, errors.New("unknown variadic input")
		}
	} else {
		result = method.Call(parameters)
	}
	if len(result) < 1 {
		s, err := m.allocString("")
		if err != nil {
			return nil, err
		}

		return []wasmer.Value{wasmer.NewI32(s)}, nil
	}

	if len(result) > 1 {
		errValue := result[1].Interface()
		if errValue != nil {
			if err, ok := errValue.(error); ok {
				return nil, err
			}
		}
	}

	res, err := m.formatParameter(result[0])
	if err != nil {
		return nil, err
	}

	s, err := m.allocString(res)
	if err != nil {
		return nil, err
	}

	return []wasmer.Value{wasmer.NewI32(int32(s))}, nil
}

func (m *WasmModule) rpcRetrieve(args []wasmer.Value) ([]wasmer.Value, error) {
	if len(args) < 2 {
		return nil, errors.New("invalid args number")
	}

	h := uintptr(args[0].I64())
	v, ok := m.handles.Load(h)
	if !ok {
		return nil, errors.New("handle lost")
	}

	f, err := m.getString(uint32(args[1].I32()))
	if err != nil {
		return nil, err
	}

	ff := strings.Split(f, ".")

	target := reflect.ValueOf(v)

	for _, fn := range ff {
		if target.Kind() == reflect.Pointer {
			target = target.Elem()
		}

		target = target.FieldByName(fn)
		if target.IsZero() {
			return nil, errors.New("target not found")
		}
	}

	res, err := m.formatParameter(target)
	if err != nil {
		return nil, err
	}

	s, err := m.allocString(res)
	if err != nil {
		return nil, err
	}

	return []wasmer.Value{wasmer.NewI32(int32(s))}, nil
}

func (m *WasmModule) parseParameters(input string) ([]reflect.Value, error) {
	if input == "" {
		return []reflect.Value{}, nil
	}

	fields := strings.Split(input, " ")
	fieldsLength := len(fields)
	if fieldsLength%2 != 0 {
		return nil, errors.New("fields not in pair")
	}

	parameters := make([]reflect.Value, fieldsLength/2)
	for i := 0; i < fieldsLength; i += 2 {
		value, err := m.getType(fields[i], fields[i+1])
		if err != nil {
			return nil, err
		}
		parameters[i/2] = value
	}

	return parameters, nil
}

func (m *WasmModule) getType(typ, val string) (reflect.Value, error) {
	switch typ {
	case "nil", "null":
		return reflect.ValueOf(nil), nil
	case "int":
		i, err := strconv.Atoi(val)
		if err != nil {
			return reflect.Value{}, err
		}
		return reflect.ValueOf(i), nil
	case "float":
		f, err := strconv.ParseFloat(val, 64)
		if err != nil {
			return reflect.Value{}, err
		}
		return reflect.ValueOf(f), nil
	case "string":
		b, err := hex.DecodeString(val)
		if err != nil {
			return reflect.Value{}, err
		}
		return reflect.ValueOf(string(b)), nil
	default:
		var t reflect2.Type
		if strings.Contains(typ, ".") {
			s := strings.SplitN(typ, ".", 2)
			t = reflect2.TypeByPackageName(s[0], s[1])
		} else {
			t = reflect2.TypeByName(typ)
		}
		if t == nil {
			return reflect.Value{}, errors.New("invalid type")
		}

		return reflect.ValueOf(t.New()), nil
	}
}

func (m *WasmModule) formatParameter(input reflect.Value) (string, error) {
	typ := input.Type()
	switch typ.Kind() {
	case reflect.Int,
		reflect.Int8,
		reflect.Int16,
		reflect.Int32,
		reflect.Int64:
		return "int " + strconv.FormatInt(input.Int(), 10), nil
	case reflect.Uint,
		reflect.Uint8,
		reflect.Uint16,
		reflect.Uint32,
		reflect.Uint64,
		reflect.Uintptr:
		return "int " + strconv.FormatUint(input.Uint(), 10), nil
	case reflect.Float32,
		reflect.Float64:
		return "float " + strconv.FormatFloat(input.Float(), 'f', -1, 64), nil
	case reflect.String:
		return "string " + hex.EncodeToString([]byte(input.String())), nil
	case reflect.Slice,
		reflect.Array:
		content := "array ("
		for i := 0; i < input.Len(); i++ {
			if i > 0 {
				content += ", "
			}
			s, err := m.formatParameter(input.Index(i))
			if err != nil {
				return "", err
			}
			content += s
		}
		content += ")"
		return content, nil
	default:
		if typ.Kind() == reflect.Pointer {
			input = input.Elem()
		}
		h := m.registerHandle(input.Interface())
		return fmt.Sprintf("handle %d", h), nil
	}
}

func (m *WasmModule) alloc(size, class int) (uint32, error) {
	allocateFun, err := m.instance.Exports.GetFunction("__new")
	if err != nil {
		return 0, err
	}

	allocateResult, err := allocateFun(size, class)
	if err != nil {
		return 0, err
	}

	inputPointer32, ok := allocateResult.(int32)
	if !ok {
		return 0, fmt.Errorf("invalid __new return type")
	}

	return uint32(inputPointer32), nil
}

func (m *WasmModule) getMemory(pointer uint32, size uint32) ([]byte, error) {
	memory, err := m.instance.Exports.GetMemory("memory")
	if err != nil {
		return nil, err
	}

	return memory.Data()[int(pointer):int(pointer+size)], nil
}

func (m *WasmModule) allocString(s string) (uint32, error) {
	runes := utf16.Encode([]rune(s))

	inputPointer, err := m.alloc(len(runes)*2, 1)
	if err != nil {
		return 0, err
	}

	buffer, err := m.getMemory(inputPointer, uint32(len(runes)*2))
	if err != nil {
		return 0, err
	}

	for i, r := range runes {
		buffer[i*2] = byte(r)
		buffer[i*2+1] = byte(r >> 8)
	}

	return inputPointer, nil
}

func (m *WasmModule) getString(pointer uint32) (string, error) {
	memory, err := m.instance.Exports.GetMemory("memory")
	if err != nil {
		return "", err
	}

	data := memory.Data()
	length := binary.LittleEndian.Uint32(data[pointer-4 : pointer])

	codes := make([]uint16, length/2)
	for i := range codes {
		codes[i] = uint16(data[int(pointer)+(i*2)]) + uint16(data[int(pointer)+(i*2)+1])>>8
	}

	runes := utf16.Decode(codes)

	return string(runes), nil
}

func (m *WasmModule) NetworkCompute(definition string) (string, error) {
	inputPointer, err := m.allocString(definition)
	if err != nil {
		return "", err
	}

	computeNetwork, err := m.instance.Exports.GetFunction("compute_network")
	if err != nil {
		return "", err
	}

	output, err := computeNetwork(int32(inputPointer))
	if err != nil {
		return "", err
	}

	outputPointer, ok := output.(int32)
	if !ok {
		return "", fmt.Errorf("invalid compute_network return")
	}

	data, err := m.getString(uint32(outputPointer))
	if err != nil {
		return "", err
	}

	return data, nil
}

func (m *WasmModule) Close() {
	m.instance.Close()
	m.store.Close()
}
