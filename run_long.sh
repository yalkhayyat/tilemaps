#!/bin/bash

docker run \
  --rm \
  -d \
  --name tilemaps-app \
  --env-file ./.env \
  -v "$(pwd)/src:/app/src" \
  -v "$(pwd)/output:/app/output" \
  tilemaps-generator \
  "$@"