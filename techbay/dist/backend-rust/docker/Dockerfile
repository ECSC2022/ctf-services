FROM ubuntu:20.04

RUN apt update
RUN apt install -y libpq-dev

RUN groupadd ubuntu && useradd -g ubuntu -u 1001 ubuntu

WORKDIR /app

ADD backend-rust private.ke[y] ./
RUN chmod +x backend-rust

RUN mkdir /app/data

RUN chown -R ubuntu:ubuntu /app

USER ubuntu
EXPOSE 3030

ENTRYPOINT ["./backend-rust"]