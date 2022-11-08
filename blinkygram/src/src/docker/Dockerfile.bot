FROM ubuntu:20.04

RUN apt-get update && apt-get install -y libssl1.1

RUN useradd bot

WORKDIR /app

RUN mkdir /app/storage && chmod 777 /app/storage

COPY ./bot ./
RUN chmod +x ./bot

USER bot

ENTRYPOINT ["./bot"]
