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

if [ "${CI_COMMIT_REF_NAME:-`git branch --show-current`}" == "master" ]; then
    IMAGE_TAG="latest";
else
    IMAGE_TAG=${CI_COMMIT_SHORT_SHA:-`git rev-parse --short HEAD`};
fi
MHUB_PORT=$(( 5000 + $RANDOM % 1000 ))

if [ "$BUILD" == "TRUE" ]; then
    COMPFILE="docker-compose.yml"
    echo "build image from source"
  else
    COMPFILE="docker-compose.image.yml"
    echo "use registry.gitlab.eox.at/maps/mapchete_hub/${IMAGE_NAME:-mhub}:${IMAGE_TAG:-latest}"
fi

echo "run docker-compose build on ${COMPFILE}"
docker-compose \
    -p $CI_JOB_ID \
    -f $COMPFILE \
    -f docker-compose.test.yml \
    build \
    --build-arg BASE_IMAGE_NAME=${BASE_IMAGE_NAME} \
    --build-arg IMAGE_TAG=${IMAGE_TAG} \
    --build-arg EOX_PYPI_TOKEN=${EOX_PYPI_TOKEN}
echo "run mhub on port ${MHUB_PORT}"
docker-compose \
    -p $CI_JOB_ID \
    -f $COMPFILE \
    -f docker-compose.test.yml \
    up \
    --exit-code-from mhub_tester
docker-compose \
    -p $CI_JOB_ID \
    -f $COMPFILE \
    -f docker-compose.test.yml \
    down \
    -v \
    --remove-orphans \
|| true
