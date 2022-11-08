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

ENV BUILDNAME=point-of-sale
WORKDIR /cantina/$BUILDNAME
# pre-copy/cache go.mod for pre-downloading dependencies and only redownloading them in subsequent builds if they change
COPY $BUILDNAME/go.mod $BUILDNAME/go.sum ./
RUN go mod tidy
COPY $BUILDNAME/. ./
RUN go build -v -o /app/$BUILDNAME -ldflags "-s -w" ./point-of-sale.go
WORKDIR /app

FROM alpine:3.16 as pos-copy
ENV BUILDNAME=point-of-sale
COPY --from=base /app/$BUILDNAME /app/pos
COPY ./point-of-sale/order-items.yaml /app
CMD ["/app/pos"]

