#!/bin/bash

REGISTRY_BASEURL="registry.gitlab.eox.at/maps/mapchete_hub"
USAGE="Usage: $(basename "$0") [-h] TAG

Build and tag docker images.

Parameters:
    -h      Show this help text and exit.
    TAG     Tag used for images. (default: current branch or 'latest' for master)
"

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

# get correct tag
TAG=${1:-$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')}
if [ "$TAG" == "master" ]; then
    TAG="latest"
fi

echo "build mhub:$TAG"
docker build -t $REGISTRY_BASEURL/mhub:$TAG . && \
docker push $REGISTRY_BASEURL/mhub:$TAG
