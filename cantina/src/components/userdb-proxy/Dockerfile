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

ENV GIN_MODE=release
ENV BUILDNAME=userdb-proxy
WORKDIR /cantina/$BUILDNAME
# pre-copy/cache go.mod for pre-downloading dependencies and only redownloading them in subsequent builds if they change
COPY $BUILDNAME/go.mod $BUILDNAME/go.sum ./
RUN go mod tidy
COPY $BUILDNAME/. ./
RUN go build -v -o /app/$BUILDNAME -ldflags "-s -w" ./userdb.go
WORKDIR /app


FROM scratch as copy
ENV BUILDNAME=userdb-proxy
COPY --from=base /app/$BUILDNAME /userdb-proxy



FROM alpine:3.16 as udb-copy
ENV BUILDNAME=userdb-proxy
RUN addgroup -S cantina && adduser -S cantina -G cantina

RUN mkdir /app
RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app
WORKDIR /app

COPY --from=base /app/$BUILDNAME /app/userdb-proxy
USER cantina
CMD ["/app/userdb-proxy"]

