#!/bin/bash

docker run -t -i --network=host --env DISPLAY=$DISPLAY --volume $XAUTH:/root/.Xauthority -v "$(pwd)":/checker dewaste2:latest localhost 1 0
