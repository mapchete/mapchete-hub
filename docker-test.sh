#!/bin/bash

REGISTRY_BASEURL="registry.gitlab.eox.at/maps/mapchete_hub"
USAGE="Usage: $(basename "$0") [-h] TAG

Test using built docker image.

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

./docker-build.sh
echo "test mhub:$TAG"
docker run --rm -it $REGISTRY_BASEURL/mhub:$TAG /bin/bash -c "pip install -e .[test] && pytest -v --cov=mapchete_hub"
