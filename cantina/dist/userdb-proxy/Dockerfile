FROM alpine:3.16

RUN addgroup -S cantina && adduser -S cantina -G cantina

WORKDIR /app

COPY ./userdb-proxy /app/udb

RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app

USER cantina

CMD ["/app/udb"]
