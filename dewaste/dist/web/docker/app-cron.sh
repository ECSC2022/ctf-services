#!/bin/bash

cmd="/usr/local/bin/php /var/www/html/cli.php"

i=0
while [ true ]
do
  if [[ $i -eq 12 ]]; then
    $cmd --cleanup-files --cleanup-database
    i=0
  fi

  $cmd --process-data-item

  sleep 5

  i=$((i+1))
done
