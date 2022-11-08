#!/bin/bash

max="$1"
if [ -z "$max" ]; then
  max=6
fi

docker-compose build
for i in $(seq 0 $max); do
  TICK=$i docker-compose up
done
