#!/usr/bin/env bash
set -e

rm -rf build

docker build -t ecsc2022-aquaeductus-wasm:latest .

CONTAINER_ID=$(docker create ecsc2022-aquaeductus-wasm:latest)
docker cp $CONTAINER_ID:/app/build .
docker rm $CONTAINER_ID
