#!/bin/bash

docker build -t registry.gitlab.eox.at/maps/mapchete_hub/mhub:testing .
docker-compose up
