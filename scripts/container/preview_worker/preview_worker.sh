#!/bin/bash

# set environment variables
MHUB_DOCKER_IMAGE_TAG="0.3"
DOCKER_BASE_IMAGE_TAG="0.2"
GITLAB_REGISTRY_TOKEN=REDACTED_API_KEY
AWS_ACCESS_KEY_ID="REDACTED_API_KEY"
AWS_SECRET_ACCESS_KEY="REDACTED_API_KEY"
BROKER_USER="mhub"
BROKER_PW="uwoo0aVo"
BROKER_IP="3.120.139.183:5672"
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MP_SATELLITE_CACHE_PATH=/mnt/data/cache
WORKER="index_worker"
QUEUE="preview_worker_queue"
HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
INDEX_OUTPUT_DIR='/mnt/data/indexes'
PREVIEW_PERMALINK='http://'$HOST_IP
SLACK_WEBHOOK_URL='REDACTED_API_KEY'
LOGLEVEL="INFO"

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

# get rgb_worker docker container
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/worker:$MHUB_DOCKER_IMAGE_TAG
retry 10 docker pull registry.gitlab.eox.at/maps/docker-base/mapserver:$DOCKER_BASE_IMAGE_TAG

# move map directory in place
mv map /mnt/data

docker run \
  --rm \
  --name=mapserver \
  -p 80:80 \
  -v /mnt/data/map/html:/html \
  -v /mnt/data/map:/map \
  -v /mnt/data/indexes:/indexes \
  -v /mnt/data/mapdata:/mapdata \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -d \
  registry.gitlab.eox.at/maps/docker-base/mapserver:$DOCKER_BASE_IMAGE_TAG
docker run \
  --rm \
  --name $WORKER \
  -e WORKER=$WORKER \
  -e QUEUE=$QUEUE \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e PREVIEW_PERMALINK=$PREVIEW_PERMALINK \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e HOST_IP=$HOST_IP \
  -e INDEX_OUTPUT_DIR=$INDEX_OUTPUT_DIR \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -e LOGLEVEL=$LOGLEVEL \
  -e LOGFILE=$LOGFILE \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/worker:$MHUB_DOCKER_IMAGE_TAG
