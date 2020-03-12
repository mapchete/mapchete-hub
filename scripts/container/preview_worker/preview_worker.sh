#!/bin/bash
REQUIRED=( AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY BROKER_USER BROKER_PW BROKER_IP GITLAB_REGISTRY_TOKEN SLACK_WEBHOOK_URL )

USAGE="Usage: $(basename "$0") [-h] TAG

Run mhub index worker and mapserver containers.

NOTE:
This script needs further environmental variables in order to start the docker container
properly:

$(for var in "${REQUIRED[@]}"; do echo " - ${var}"; done)

These variables are also attempted to be read from an .env file from this directory.

Parameters:
    -h      Show this help text and exit.
    TAG     Tag used for mhub image. (default: stable)
"

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

# load variables from .env file if possible
if [ -f ".env" ]; then
  echo "load variables from .env file"
  export $(cat .env | xargs)
fi
for var in "${REQUIRED[@]}"; do
  if [[ -z ${!var+x} ]];
  then
      echo "variable ${var} is not set"
      exit 0
  fi
done;

# set mhub variables
HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
LOCAL_VOLUME_DIR=${LOCAL_VOLUME_DIR:-"/mnt/data"}
MAPSERVER_IMAGE_TAG="0.2"
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_CELERY_SLACK=${MHUB_CELERY_SLACK:-"TRUE"}
MHUB_DOCKER_IMAGE_TAG=${1:-"stable"}
MHUB_INDEX_OUTPUT_DIR=${MHUB_INDEX_OUTPUT_DIR:-"/mnt/data/indexes"}
MHUB_LOGLEVEL=${MHUB_LOGLEVEL:-"INFO"}
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_QUEUE=${MHUB_QUEUE:-"index_queue"}
MHUB_WORKER="index_worker"
MP_SATELLITE_CACHE_PATH=${MP_SATELLITE_CACHE_PATH:-"/mnt/data/cache"}
PREVIEW_PERMALINK=${PREVIEW_PERMALINK:-"http://"$HOST_IP"/geodetic.html"}

echo "use mapchete_hub ${MHUB_DOCKER_IMAGE_TAG}"

# from https://gist.github.com/sj26/88e1c6584397bb7c13bd11108a579746
function retry {
  local retries=$1
  shift

  local count=0
  until "$@"; do
    exit=$?
    wait=$((2 ** $count))
    count=$(($count + 1))
    if [ $count -lt $retries ]; then
      echo "Retry $count/$retries exited $exit, retrying in $wait seconds..."
      sleep $wait
    else
      echo "Retry $count/$retries exited $exit, no more retries left."
      return $exit
    fi
  done
  return 0
}

# install docker if not available
if ! [ -x "$(command -v docker)" ]; then
  echo "Error: docker is not installed." >&2
  # install and configure docker
  curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh
  sudo newgrp docker
  sudo usermod -aG docker ubuntu
  sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
  sudo chmod g+rwx $"/home/$USER/.docker" -R
  # make dirs
  sudo mkdir -p ${LOCAL_VOLUME_DIR}/log
  sudo chown -R ubuntu:ubuntu ${LOCAL_VOLUME_DIR}
  # install tools
  sudo apt install -y htop
fi

# get docker images
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG
retry 10 docker pull registry.gitlab.eox.at/maps/docker-base/mapserver:$MAPSERVER_IMAGE_TAG

# move directories in place
cp -R html ${LOCAL_VOLUME_DIR}/
# map directory shall contain "geodetic" and "mercator" subdirectories with mapfiles
cp -R map ${LOCAL_VOLUME_DIR}/
# insert mapcache IP for WMTS layer
sed "s/MHUB_MAPCACHE_IP/${MHUB_MAPCACHE_IP}/g" html/s2maps.js > ${LOCAL_VOLUME_DIR}/html/s2maps.js
# insert AWS credentials so mapserver can access bucket
printf "CONFIG \"AWS_ACCESS_KEY_ID\" \"${AWS_ACCESS_KEY_ID}\"\nCONFIG \"AWS_SECRET_ACCESS_KEY\" \"${AWS_SECRET_ACCESS_KEY}\"\n" > ${LOCAL_VOLUME_DIR}/map/.credentials.map

# try to stop container if they are running
docker container stop mapserver ${MHUB_WORKER} || true

# run docker containers
docker run \
  --rm \
  --name=mapserver \
  -p 80:80 \
  -v ${LOCAL_VOLUME_DIR}/html:/html \
  -v ${LOCAL_VOLUME_DIR}/map:/map \
  -v ${LOCAL_VOLUME_DIR}/indexes:/indexes \
  -v ${LOCAL_VOLUME_DIR}/mapdata:/mapdata \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -d \
  registry.gitlab.eox.at/maps/docker-base/mapserver:$MAPSERVER_IMAGE_TAG
docker run \
  --rm \
  --name $MHUB_WORKER \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e HOST_IP=$HOST_IP \
  -e LOGFILE=$LOGFILE \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_INDEX_OUTPUT_DIR=$MHUB_INDEX_OUTPUT_DIR \
  -e MHUB_QUEUE=$MHUB_QUEUE \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_WORKER=$MHUB_WORKER \
  -e PREVIEW_PERMALINK=$PREVIEW_PERMALINK \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -v ${LOCAL_VOLUME_DIR}:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py worker -n $MHUB_WORKER -q $MHUB_QUEUE --loglevel=$MHUB_LOGLEVEL
