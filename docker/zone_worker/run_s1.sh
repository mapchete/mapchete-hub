#!/bin/bash

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

# install docker
curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
sudo chmod g+rwx "/home/$USER/.docker" -R

# make dirs
sudo mkdir -p /mnt/data/log
sudo mkdir -p /mnt/data/cache
sudo chown -R ubuntu:ubuntu /mnt/data
# install tools
sudo apt install -y htop

# log into registry
CI_JOB_TOKEN=REDACTED_API_KEY
retry 10 docker login -u gitlab-ci-token -p $CI_JOB_TOKEN registry.gitlab.eox.at
retry 10 docker pull registry.gitlab.eox.at/maps/mapchete_hub/base_worker_s1:0.8

# set environment and run container
LOGLEVEL='DEBUG'
LOGFILE=/mnt/data/log/worker.log
AWS_S3_ENDPOINT='obs.eu-de.otc.t-systems.com'
AWS_ACCESS_KEY_ID='GZMKTK8LQMPLWZ1NIOLZ'
AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY'
MHUB_BROKER_URL='amqp://s1processor:REDACTED_API_KEY@192.168.1.154:5672//'
MHUB_RESULT_BACKEND='rpc://s1processor:REDACTED_API_KEY@192.168.1.154:5672//'
MP_SATELLITE_CACHE_PATH=/mnt/data/cache
WORKER='zone_worker'
QUEUE='zone_worker_queue'
docker run \
  --rm \
  --name $WORKER \
  -e WORKER=$WORKER \
  -e QUEUE=$QUEUE \
  -e AWS_S3_ENDPOINT=$AWS_S3_ENDPOINT \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MP_SATELLITE_CACHE_PATH=$MP_SATELLITE_CACHE_PATH \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e GML_SKIP_CORRUPTED_FEATURES=YES \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e LOGLEVEL=$LOGLEVEL \
  -e LOGFILE=$LOGFILE \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/base_worker_s1:0.8