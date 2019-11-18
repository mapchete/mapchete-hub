#!/bin/bash

# set environment variables
MHUB_DOCKER_IMAGE_TAG=${1:-"stable"}
LOGLEVEL="INFO"

AWS_ACCESS_KEY_ID="REDACTED_API_KEY"
AWS_SECRET_ACCESS_KEY="REDACTED_API_KEY"
BROKER_USER="mhub"
BROKER_PW="uwoo0aVo"
BROKER_IP="3.120.139.183:5672"
GITLAB_REGISTRY_TOKEN=REDACTED_API_KEY
GUNICORN_CMD_ARGS="--bind 0.0.0.0:5000 --log-level $LOGLEVEL --workers 4 --threads 4 --worker-class=gthread --worker-tmp-dir /dev/shm"
LOCAL_VOLUME_DIR=/mnt/data
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_CELERY_SLACK=TRUE
MHUB_CONFIG_DIR="/mnt/data/"
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_STATUS_GPKG="/mnt/data/status.gpkg"
SLACK_WEBHOOK_URL="REDACTED_API_KEY"


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
  sudo mkdir -p /mnt/data/log
  sudo chown -R ubuntu:ubuntu /mnt/data
  # install tools
  sudo apt install -y htop
fi

# get rgb_worker docker container
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG

# set environment and run containers
docker run \
  --rm \
  --name=monitor \
  -v $LOCAL_VOLUME_DIR:/mnt/data \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_STATUS_GPKG=$MHUB_STATUS_GPKG \
  -e LOGLEVEL=$LOGLEVEL \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py monitor --loglevel=$LOGLEVEL
docker run \
  --rm \
  --name=server \
  -p 5000:5000 \
  -v $LOCAL_VOLUME_DIR:/mnt/data \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e GUNICORN_CMD_ARGS="$GUNICORN_CMD_ARGS" \
  -e LOGLEVEL=$LOGLEVEL \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_STATUS_GPKG=$MHUB_STATUS_GPKG \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  gunicorn "mapchete_hub.application:flask_app()"
