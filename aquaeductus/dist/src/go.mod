module aquaeductus

go 1.19

require (
	github.com/gin-contrib/gzip v0.0.6
	github.com/gin-contrib/sessions v0.0.5
	github.com/gin-contrib/size v0.0.0-20220829131622-0fc0bc875336
	github.com/gin-gonic/gin v1.8.1
	github.com/go-playground/validator/v10 v10.11.0
	github.com/go-sql-driver/mysql v1.6.0
	github.com/json-iterator/go v1.1.12
	github.com/modern-go/reflect2 v1.0.2
	github.com/rs/zerolog v1.28.0
	github.com/speps/go-hashids/v2 v2.0.1
	github.com/wasmerio/wasmer-go v1.0.4
	golang.org/x/crypto v0.0.0-20220829220503-c86fa9a7ed90
	gorm.io/driver/mysql v1.3.6
	gorm.io/gorm v1.23.8
)

// https://github.com/wasmerio/wasmer-go/pull/333
replace github.com/wasmerio/wasmer-go => github.com/gzigzigzeo/wasmer-go v1.0.5-0.20220421041604-32e79da17c08

require (
	github.com/gin-contrib/sse v0.1.0 // indirect
	github.com/go-playground/locales v0.14.0 // indirect
	github.com/go-playground/universal-translator v0.18.0 // indirect
	github.com/goccy/go-json v0.9.11 // indirect
	github.com/google/go-cmp v0.5.8 // indirect
	github.com/gorilla/context v1.1.1 // indirect
	github.com/gorilla/securecookie v1.1.1 // indirect
	github.com/gorilla/sessions v1.2.1 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/leodido/go-urn v1.2.1 // indirect
	github.com/mattn/go-colorable v0.1.13 // indirect
	github.com/mattn/go-isatty v0.0.16 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/pelletier/go-toml/v2 v2.0.5 // indirect
	github.com/ugorji/go/codec v1.2.7 // indirect
	golang.org/x/net v0.0.0-20220826154423-83b083e8dc8b // indirect
	golang.org/x/sys v0.0.0-20220829200755-d48e67d00261 // indirect
	golang.org/x/text v0.3.7 // indirect
	google.golang.org/protobuf v1.28.1 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
)
