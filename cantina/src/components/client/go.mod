module cantina/client

go 1.19

require (
	cantina/common v0.0.0-00010101000000-000000000000
	cantina/gateway v0.0.0-00010101000000-000000000000
	github.com/gordonklaus/portaudio v0.0.0-20220320131553-cc649ad523c1
	github.com/vmihailenco/msgpack v4.0.4+incompatible
	golang.org/x/sys v0.0.0-20220907062415-87db552b00fd
)

require (
	github.com/golang/protobuf v1.3.1 // indirect
	github.com/vmihailenco/msgpack/v5 v5.3.5 // indirect
	github.com/vmihailenco/tagparser/v2 v2.0.0 // indirect
	github.com/zekroTJA/timedmap v1.4.0 // indirect
	golang.org/x/net v0.0.0-20190603091049-60506f45cf65 // indirect
	google.golang.org/appengine v1.6.7 // indirect
	gopkg.in/check.v1 v1.0.0-20201130134442-10cb98267c6c // indirect
)

replace cantina/gateway => ../gateway

replace cantina/common => ../gocommon
