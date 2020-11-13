#!/bin/bash
#               vCPU  Memory (GiB)  Instance Storage (GB)   Linux/UNIX Usage
# m5dn.2xlarge     8        32 GiB       1 x 300 NVMe SSD    $0.648 per Hour

#########################################
# parameters from generate_user_data.sh #
#########################################
# insert params here


#############
# from .env #
#############
# insert .env contents here


###################
# mount_volume.sh #
###################
DATA_DIR="/mnt/data"
# find out name for extra volume
VOLUME="/dev/$(lsblk | grep ${VOLUME_SIZE}G | head -n1 | sed -e 's/\s.*$//')"

sudo mkfs -t ext4 ${VOLUME}
sudo mkdir -p ${DATA_DIR}
sudo mount ${VOLUME} ${DATA_DIR}
sudo chown -R ubuntu: ${DATA_DIR}


#############
# worker.sh #
#############

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
