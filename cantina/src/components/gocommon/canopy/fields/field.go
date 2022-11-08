package fields

type Field interface {
	FieldSize() int
	FromBytes([]byte) (int, error)
	ToBytes([]byte) []byte
}
