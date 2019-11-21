#!/bin/bash
REQUIRED=( AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY BROKER_USER BROKER_PW BROKER_IP GITLAB_REGISTRY_TOKEN SLACK_WEBHOOK_URL )

USAGE="Usage: $(basename "$0") [-h] TAG

Run mhub worker container.

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
LOCAL_VOLUME_DIR=${LOCAL_VOLUME_DIR:-"/mnt/data"}
MHUB_BROKER_URL=$"amqp://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_CELERY_SLACK=${MHUB_CELERY_SLACK:-"TRUE"}
MHUB_DOCKER_IMAGE_TAG=${1:-"stable"}
MHUB_LOGLEVEL=${MHUB_LOGLEVEL:-"INFO"}
MHUB_RESULT_BACKEND=$"rpc://${BROKER_USER}:${BROKER_PW}@${BROKER_IP}//"
MHUB_QUEUE=${MHUB_QUEUE:-"execute_queue"}
MHUB_WORKER="execute_worker"
MP_SATELLITE_CACHE_PATH=${MP_SATELLITE_CACHE_PATH:-"/mnt/data/cache"}

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

# try to stop container if they are running
docker container stop ${MHUB_WORKER} || true

# run docker containers
docker run \
  --rm \
  --name=${MHUB_WORKER} \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e GML_SKIP_CORRUPTED_FEATURES=YES \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e MHUB_BROKER_URL=${MHUB_BROKER_URL} \
  -e MHUB_CELERY_SLACK=${MHUB_CELERY_SLACK} \
  -e MHUB_CONFIG_DIR=${MHUB_CONFIG_DIR} \
  -e MHUB_QUEUE=${MHUB_QUEUE} \
  -e MHUB_WORKER=${MHUB_WORKER} \
  -e MHUB_RESULT_BACKEND=${MHUB_RESULT_BACKEND} \
  -e MP_SATELLITE_CACHE_PATH=${MP_SATELLITE_CACHE_PATH} \
  -e SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL} \
  -v ${LOCAL_VOLUME_DIR}:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mhub:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py worker -n ${MHUB_WORKER} -q ${MHUB_QUEUE} --loglevel=${MHUB_LOGLEVEL}
