#!/bin/bash

CI_JOB_ID=${CI_JOB_ID:-"local_test"}
BASE_IMAGE_NAME=${BASE_IMAGE_NAME:-"mapchete"}
MHUB_PORT=$(( 5000 + $RANDOM % 1000 ))

docker-compose \
    -p $CI_JOB_ID \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    build \
    --build-arg BASE_IMAGE_NAME=${BASE_IMAGE_NAME} \
    --build-arg EOX_PYPI_TOKEN=${EOX_PYPI_TOKEN}

echo "run mhub on port ${MHUB_PORT}"

docker-compose \
    -p $CI_JOB_ID \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    up \
    --exit-code-from mhub_tester
docker-compose \
    -p $CI_JOB_ID \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    down \
    -v \
    --rmi all \
    --remove-orphans \
|| true
docker-compose \
    -p $CI_JOB_ID \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    rm \
    -fv \
|| true
