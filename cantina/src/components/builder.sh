#!/usr/bin/bash

docker buildx build --target copy -o out --file userdb-proxy/Dockerfile .
docker buildx build --target copy -o out --file jukebox-proxy/Dockerfile .
