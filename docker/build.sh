#!/bin/bash
AVAILABLE_IMAGES=("base_image base_image_s1 worker worker_s1 server monitor")
REGISTRY_BASEURL="registry.gitlab.eox.at/maps/mapchete_hub"
USAGE="Usage: $(basename "$0") [-h] IMAGE TAG

Build and tag docker images.

Parameters:
    -h      Show this help text and exit.
    IMAGE   Either ':all:'' or one of [$AVAILABLE_IMAGES].
    TAG     Tag used for images. (default: 'latest')
"

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
elif [ "$1" == "" ]; then
    echo "IMAGE not provided."
    echo "$USAGE"
    exit 0
fi

IMAGE=$1
TAG=${2:-latest}

if [ "$IMAGE" == ":all:" ]; then
    IMAGES=$AVAILABLE_IMAGES
elif [[ ${AVAILABLE_IMAGES} =~ (^|[[:space:]])${IMAGE}($|[[:space:]]) ]]; then
    IMAGES=("$IMAGE")
else
    echo "IMAGE $IMAGE not found."
    exit 0
fi

for IMAGE in $IMAGES
    do echo $IMAGE:$TAG;
    docker build --no-cache -t $REGISTRY_BASEURL/$IMAGE:$TAG $IMAGE/ && \
    docker push $REGISTRY_BASEURL/$IMAGE:$TAG
done
