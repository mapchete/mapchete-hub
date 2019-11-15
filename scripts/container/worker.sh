#!/bin/bash

# set environment variables
MHUB_DOCKER_IMAGE_TAG=${1:-"stable"}
MHUB_WORKER="execute_worker"
MHUB_QUEUE="execute_queue"
LOGLEVEL="DEBUG"

GITLAB_REGISTRY_TOKEN=REDACTED_API_KEY
AWS_ACCESS_KEY_ID="REDACTED_API_KEY"
AWS_SECRET_ACCESS_KEY="REDACTED_API_KEY"
BROKER_USER="mhub"
BROKER_PW="uwoo0aVo"
BROKER_IP="3.120.139.183:5672"
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MP_SATELLITE_CACHE_PATH=/mnt/data/cache

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
  sudo mkdir -p /mnt/data/log
  sudo chown -R ubuntu:ubuntu /mnt/data
  # install tools
  sudo apt install -y htop
fi

# get docker images
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG

# set environment and run containers
docker run \
  --rm \
  --name=$MHUB_WORKER \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e GML_SKIP_CORRUPTED_FEATURES=YES \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e LOGFILE=$LOGFILE \
  -e LOGLEVEL=$LOGLEVEL \
  -e MHUB_WORKER=$MHUB_WORKER \
  -e MHUB_QUEUE=$MHUB_QUEUE \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MP_SATELLITE_CACHE_PATH=$MP_SATELLITE_CACHE_PATH \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py worker -n $MHUB_WORKER -q $MHUB_QUEUE --loglevel=$LOGLEVEL
