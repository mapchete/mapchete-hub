#!/bin/bash
REQUIRED=( MONGO_INITDB_ROOT_USERNAME MONGO_INITDB_ROOT_PASSWORD )

USAGE="Usage: $(basename "$0") [-h] TAG

Run mongodb.

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

# try to stop container if they are running
docker container stop broker db || true

# run docker containers
docker run \
  --name=broker \
  --rm \
  -e MONGO_INITDB_ROOT_USERNAME \
  -e MONGO_INITDB_ROOT_PASSWORD \
  -p 27017:27017/tcp \
  -v `pwd`/mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js \
  -d \
  mongo:4.2.7-bionic \
  --bind_ip_all

docker run \
  --name=db \
  -e MONGO_INITDB_ROOT_USERNAME \
  -e MONGO_INITDB_ROOT_PASSWORD \
  -p 27018:27017/tcp \
  -v `pwd`/mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js \
  -d \
  mongo:4.2.7-bionic \
  --bind_ip_all || \
docker container start db
