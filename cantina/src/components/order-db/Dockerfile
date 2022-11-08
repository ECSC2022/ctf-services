FROM golang:1.19-alpine as base

#Set build arguments
ARG BUILDOS
ARG BUILDARCH
ARG BUILDNAME

RUN apk add build-base

WORKDIR /cantina/gocommon
COPY gocommon/go.mod gocommon/go.sum ./
RUN go mod tidy
COPY gocommon/. ./

RUN mkdir /app && chown -R 1000:1000 /app

ENV BUILDNAME=order-db
WORKDIR /cantina/$BUILDNAME
# pre-copy/cache go.mod for pre-downloading dependencies and only redownloading them in subsequent builds if they change
COPY $BUILDNAME/go.mod $BUILDNAME/go.sum ./
RUN go mod tidy
COPY $BUILDNAME/. ./
RUN go build -v -o /app/$BUILDNAME -ldflags "-s -w" ./order-db.go
WORKDIR /app

FROM alpine:3.16 as odb-copy
ENV BUILDNAME=order-db
COPY --from=base /app/$BUILDNAME /app/odb
CMD ["/app/odb"]

