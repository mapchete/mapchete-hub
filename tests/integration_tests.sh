#!/bin/bash

docker-compose build
docker-compose \
    -f ../docker-compose.yml \
    -f ../docker-compose.test.yml up \
    --exit-code-from mhub_tester
docker-compose rm -fv
