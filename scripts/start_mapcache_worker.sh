#!/bin/bash
REQUIRED=( AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY GITLAB_REGISTRY_TOKEN )

USAGE="Usage: $(basename "$0") [-h]

Run mapcache instance hosting the WMTS preview.

NOTE:
This script needs further environmental variables in order to start the docker container
properly:

$(for var in "${REQUIRED[@]}"; do echo " - ${var}"; done)

These variables are also attempted to be read from an .env file from this directory.

Parameters:
    -h, --help              Show this help text and exit.
    -t, --tag               Tag used for mhub image. (default: stable)
"

while [ $# -gt 0 ]; do
  case "$1" in
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
CACHE_VERSION="v1.0.0"
HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
LOCAL_VOLUME_DIR=${LOCAL_VOLUME_DIR:-"/mnt/data"}
MAPCACHE_IMAGE_TAG=${TAG}

echo "use registry.gitlab.eox.at/maps/docker-base/mapcache:$MAPCACHE_IMAGE_TAG"

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
  sudo mkdir -p ${LOCAL_VOLUME_DIR}/caches
  sudo mkdir -p ${LOCAL_VOLUME_DIR}/config
  sudo chown -R ubuntu:ubuntu ${LOCAL_VOLUME_DIR}
  # install tools
  sudo apt install -y htop
fi

# get docker images
retry 10 docker login -u gitlab-ci-token -p $GITLAB_REGISTRY_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/docker-base/mapcache:$MAPCACHE_IMAGE_TAG

# move mapcache.xml in place
sed "s/CACHE_VERSION/${CACHE_VERSION}/g; s/MHUB_PREVIEW_IP/${MHUB_PREVIEW_IP}/g" mapcache.xml > ${LOCAL_VOLUME_DIR}/config/mapcache.xml

# try to stop container if they are running
docker container stop mapcache || true

# run docker containers
docker run \
  --rm \
  --name=mapcache \
  -p 8080:80 \
  -v ${LOCAL_VOLUME_DIR}/caches:/var/sig/tiles \
  -v ${LOCAL_VOLUME_DIR}/config:/etc/mapcache/ \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -d \
  registry.gitlab.eox.at/maps/docker-base/mapcache:$MAPCACHE_IMAGE_TAG
