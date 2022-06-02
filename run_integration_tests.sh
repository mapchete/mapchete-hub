#!/bin/bash

BUILD="FALSE"

while getopts b: flag
do
    case "${flag}" in
        b) BUILD="TRUE";;
    esac
done

CI_JOB_ID=${CI_JOB_ID:-"local_test"}
CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE:-"registry.gitlab.eox.at/maps/docker-base"}
BASE_IMAGE_NAME=${BASE_IMAGE_NAME:-"mapchete"}
IMAGE_NAME=${IMAGE_NAME:-mhub}
export IMAGE_TAG=${CI_COMMIT_SHORT_SHA:-`git rev-parse --short HEAD`};
export MHUB_PORT=$(( 5000 + $RANDOM % 1000 ))

if [ "$BUILD" == "TRUE" ]; then
    COMPFILE="docker-compose.yml"
    TESTFILE="docker-compose.test.yml"
    echo "build image from source"
    docker-compose \
        -p $CI_JOB_ID \
        -f $COMPFILE \
        -f docker-compose.test.yml \
        build \
        --network host \
        --build-arg BASE_IMAGE_NAME=${BASE_IMAGE_NAME} \
        --build-arg IMAGE_TAG=${IMAGE_TAG} \
        --build-arg EOX_PYPI_TOKEN=${EOX_PYPI_TOKEN} || exit 1
else
    COMPFILE="docker-compose.image.yml"
    TESTFILE="docker-compose.image.test.yml"
    echo "build mhub image registry.gitlab.eox.at/maps/mapchete_hub/${IMAGE_NAME:-mhub}:${IMAGE_TAG}"
    docker build \
        --network host \
        --build-arg BASE_IMAGE_NAME=${BASE_IMAGE_NAME} \
        --build-arg EOX_PYPI_TOKEN=${EOX_PYPI_TOKEN} \
        -t registry.gitlab.eox.at/maps/mapchete_hub/${IMAGE_NAME:-mhub}:${IMAGE_TAG} \
        . || exit 1
fi

echo "run mhub on port ${MHUB_PORT}"
docker-compose \
    -p $CI_JOB_ID \
    -f $COMPFILE \
    -f $TESTFILE \
    up \
    --exit-code-from mhub_tester || exit 1
docker-compose \
    -p $CI_JOB_ID \
    -f $COMPFILE \
    -f $TESTFILE \
    down \
    -v \
    --remove-orphans \
|| true
