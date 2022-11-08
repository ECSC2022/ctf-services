FROM alpine:3.16

RUN addgroup -S cantina && adduser -S cantina -G cantina

WORKDIR /app

COPY ./gateway /app/gateway

RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app

USER cantina
EXPOSE 10020

CMD ["/app/gateway"]
