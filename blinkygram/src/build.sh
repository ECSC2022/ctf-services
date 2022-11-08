#!/bin/sh

sudo docker build -t ecsc22-service-5-builder . && \
sudo docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$PWD/../":/buildroot \
    ecsc22-service-5-builder "$@"
