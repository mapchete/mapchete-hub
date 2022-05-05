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
TAG=${1:-$(git rev-parse --short HEAD)}
if [ "$TAG" == "master" ]; then
    TAG="latest"
fi

echo "build mhub:$TAG"
docker build --build-arg EOX_PYPI_TOKEN=${EOX_PYPI_TOKEN} -t $REGISTRY_BASEURL/mhub:$TAG .
