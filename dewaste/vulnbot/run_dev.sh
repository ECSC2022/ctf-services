#!/bin/bash
set -e

docker build -t dewastebot:latest .
docker run -t -i --network=host --env DISPLAY=$DISPLAY --volume $XAUTH:/root/.Xauthority -v $PWD:/checker dewastebot:latest localhost 1 20
