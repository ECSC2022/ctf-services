FROM alpine:3.16

RUN addgroup -S cantina && adduser -S cantina -G cantina

WORKDIR /app

COPY ./pos /app/pos
COPY ./static /static
COPY ./order-items.yaml /app

RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app

USER cantina
EXPOSE 10021

CMD ["/app/pos"]
