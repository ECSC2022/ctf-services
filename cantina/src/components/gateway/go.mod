module cantina/gateway

go 1.19

replace cantina/common => ../gocommon

require (
	cantina/common v0.0.0-00010101000000-000000000000
	github.com/vmihailenco/msgpack/v5 v5.3.5
)

require github.com/zekroTJA/timedmap v1.4.0 // indirect

require (
	github.com/vmihailenco/tagparser/v2 v2.0.0 // indirect
	golang.org/x/sys v0.0.0-20220907062415-87db552b00fd
)
