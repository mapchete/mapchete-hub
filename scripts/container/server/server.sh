#!/bin/bash
REQUIRED=( AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY BROKER_USER BROKER_PW BROKER_IP GITLAB_REGISTRY_TOKEN SLACK_WEBHOOK_URL )

USAGE="Usage: $(basename "$0") [-h] TAG

Run mhub server and monitor containers.

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
GUNICORN_THREADS=${GUNICORN_THREADS:-"4"}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-"4"}
LOCAL_VOLUME_DIR=/mnt/data
MHUB_DOCKER_IMAGE_TAG=${1:-"stable"}
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_CONFIG_DIR="/mnt/data/"
MHUB_LOGLEVEL=${MHUB_LOGLEVEL:-"INFO"}
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_QUEUE=${MHUB_QUEUE:-"execute_queue"}
MHUB_STATUS_GPKG="/mnt/data/status.gpkg"
MHUB_WORKER="execute_worker"
MP_SATELLITE_CACHE_PATH=${MP_SATELLITE_CACHE_PATH:-"/mnt/data/cache"}
PORT=${PORT:-"5000"}

GUNICORN_CMD_ARGS="--bind 0.0.0.0:${PORT} --log-level ${MHUB_LOGLEVEL} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --worker-class=gthread --worker-tmp-dir /dev/shm"

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
  sudo chmod g+rwx "/home/$USER/.docker" -R
  # make dirs
  sudo mkdir -p ${LOCAL_VOLUME_DIR}/log
  sudo chown -R ubuntu:ubuntu ${LOCAL_VOLUME_DIR}
  # install tools
  sudo apt install -y htop
fi

# get rgb_worker docker container
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG

# try to stop container if they are running
docker container stop monitor server || true

# run docker containers
docker run \
  --rm \
  --name=monitor \
  -d \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_STATUS_GPKG=$MHUB_STATUS_GPKG \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -v ${LOCAL_VOLUME_DIR}:/mnt/data \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py monitor --loglevel=$MHUB_LOGLEVEL
docker run \
  --rm \
  --name=server \
  -d \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e GUNICORN_CMD_ARGS="$GUNICORN_CMD_ARGS" \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_STATUS_GPKG=$MHUB_STATUS_GPKG \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -p ${PORT}:${PORT} \
  -v ${LOCAL_VOLUME_DIR}:/mnt/data \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  gunicorn "mapchete_hub.application:flask_app()"
