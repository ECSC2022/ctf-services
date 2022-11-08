module cantina/keyserver

go 1.19

require (
	cantina/common v0.0.0-00010101000000-000000000000
	github.com/vmihailenco/msgpack/v5 v5.3.5
	golang.org/x/exp v0.0.0-20220909182711-5c715a9e8561
)

require (
	github.com/vmihailenco/tagparser/v2 v2.0.0 // indirect
	golang.org/x/crypto v0.0.0-20220829220503-c86fa9a7ed90 // indirect
	golang.org/x/sys v0.0.0-20220907062415-87db552b00fd // indirect
)

replace cantina/common => ../gocommon
