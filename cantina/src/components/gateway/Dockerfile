FROM golang:1.19-alpine as base

WORKDIR /cantina/gocommon

#Set build arguments
ARG BUILDOS
ARG BUILDARCH
ARG BUILDNAME

COPY gocommon/go.mod gocommon/go.sum ./
RUN go mod tidy
COPY gocommon/. ./
RUN mkdir /app && chown -R 1000:1000 /app

ENV BUILDNAME=gateway

WORKDIR /cantina/$BUILDNAME
# pre-copy/cache go.mod for pre-downloading dependencies and only redownloading them in subsequent builds if they change
COPY $BUILDNAME/go.mod $BUILDNAME/go.sum ./
RUN go mod tidy
COPY $BUILDNAME/. ./
RUN go build -v -o /app/$BUILDNAME -ldflags "-s -w" ./main.go
WORKDIR /app

FROM alpine:3.16 as gw-copy
ENV BUILDNAME=gateway
COPY --from=base /app/gateway /app/gateway
CMD ["/app/gateway"]

