FROM alpine:3.16

RUN addgroup -S cantina && adduser -S cantina -G cantina

WORKDIR /app

COPY ./ksv /app/ksv

RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app

USER cantina

CMD ["/app/ksv"]
