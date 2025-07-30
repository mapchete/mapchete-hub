#!/bin/bash

export MHUB_PORT=$(( 5000 + $RANDOM % 1000 ))

COMPFILE="docker-compose.yml"
TESTFILE="docker-compose.test.yml"
echo "build image from source"
docker compose \
    -f $COMPFILE \
    -f docker-compose.test.yml \
    build || exit 1

echo "run mhub on port ${MHUB_PORT}"
docker compose \
    -f $COMPFILE \
    -f $TESTFILE \
    up \
    --exit-code-from mhub_tester || exit 1
docker compose \
    -f $COMPFILE \
    -f $TESTFILE \
    down \
    -v \
    --remove-orphans \
|| true
