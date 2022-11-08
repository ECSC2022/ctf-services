FROM alpine:3.16

RUN addgroup -S cantina && adduser -S cantina -G cantina

WORKDIR /app

COPY ./jukebox-proxy /app/jukebox
COPY ./static /app/static

RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app

USER cantina
EXPOSE 10025

CMD ["/app/jukebox"]
