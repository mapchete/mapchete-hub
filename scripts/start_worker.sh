#!/bin/bash
REQUIRED=( AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY MHUB_BROKER_URI MHUB_RESULT_BACKEND_URI GITLAB_REGISTRY_TOKEN MHUB_SLACK_WEBHOOK_URL )

USAGE="Usage: $(basename "$0") [-h]

Run mhub worker container.

NOTE:
This script needs further environmental variables in order to start the docker container
properly:

$(for var in "${REQUIRED[@]}"; do echo " - ${var}"; done)

These variables are also attempted to be read from an .env file from this directory.

Parameters:
    -h, --help              Show this help text and exit.
    -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
    -t, --tag               Tag used for mhub image. (default: stable)
"

while [ $# -gt 0 ]; do
  case "$1" in
    --image*|-i*)
      if [[ "$1" != *=* ]]; then shift; fi
      IMAGE="${1#*=}"
      ;;
    --tag*|-t*)
      if [[ "$1" != *=* ]]; then shift; fi
      TAG="${1#*=}"
      ;;
    --help|-h)
      printf "$USAGE" # Flag argument
      exit 0
      ;;
    *)
      >&2 printf "Error: Invalid argument\n"
      exit 1
      ;;
  esac
  shift
done

IMAGE=${IMAGE:-"mhub"}
TAG=${TAG:-"stable"}

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
MHUB_CELERY_SLACK=${MHUB_CELERY_SLACK:-"TRUE"}
MHUB_DOCKER_IMAGE=${IMAGE:-"mhub"}
MHUB_DOCKER_IMAGE_TAG=${TAG:-"stable"}
MHUB_LOGLEVEL=${MHUB_LOGLEVEL:-"INFO"}
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
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/$MHUB_DOCKER_IMAGE:$MHUB_DOCKER_IMAGE_TAG

# try to stop container if they are running
docker container stop ${MHUB_WORKER} || true

# run docker containers
docker run \
  --rm \
  --name=${MHUB_WORKER} \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e MHUB_BROKER_URI=$MHUB_BROKER_URI \
  -e MHUB_CELERY_SLACK=$MHUB_CELERY_SLACK \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MHUB_RESULT_BACKEND_URI=$MHUB_RESULT_BACKEND_URI \
  -e MHUB_STATUS_DB_URI=$MHUB_STATUS_DB_URI \
  -e MHUB_QUEUE=$MHUB_QUEUE \
  -e MHUB_WORKER=$MHUB_WORKER \
  -e MP_SATELLITE_CACHE_PATH=$MP_SATELLITE_CACHE_PATH \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -v ${LOCAL_VOLUME_DIR}:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/$MHUB_DOCKER_IMAGE:$MHUB_DOCKER_IMAGE_TAG \
  ./manage.py worker -n ${MHUB_WORKER} -q ${MHUB_QUEUE} --loglevel=${MHUB_LOGLEVEL}
