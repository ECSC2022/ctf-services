##########################################################################################################
# Builder
##########################################################################################################
FROM golang:1.19 AS builder

RUN apt-get update  \
 && apt-get install -y \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY go.mod .
COPY go.sum .

RUN go mod download

COPY . .

RUN GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build -ldflags="-s -w" -o aquaeductus



##########################################################################################################
# Final
##########################################################################################################
FROM debian:bullseye-slim AS final

RUN apt-get update \
 && apt-get install -y wget tar \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir /tmp/wasmer \
 && wget -O /tmp/wasmer/wasmer-linux-amd64.tar.gz https://github.com/wasmerio/wasmer/releases/download/2.3.0/wasmer-linux-amd64.tar.gz \
 && cd /tmp/wasmer \
 && tar xvzf wasmer-linux-amd64.tar.gz \
 && cp lib/libwasmer.so /lib/x86_64-linux-gnu/ \
 && cd \
 && rm -rf /tmp/wasmer

WORKDIR /app

COPY *.wasm wasm/

COPY public/assets assets
COPY --from=builder /app/views views
COPY --from=builder /app/aquaeductus aquaeductus

CMD ["/app/aquaeductus", "-port", "10041", "-wasm-module", "/app/wasm/release.wasm"]
