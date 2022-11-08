#!/bin/bash

echo "Starting background tasks"
/app-cron.sh &

echo "Starting server"
apache2-foreground