#!/bin/bash

CI_JOB_TOKEN=REDACTED_API_KEY
LOGLEVEL=DEBUG
LOGFILE=/mnt/data/log/worker.log

# install docker
curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
sudo chmod g+rwx "/home/$USER/.docker" -R

# get rgb_worker docker container
docker login -u gitlab-ci-token -p $CI_JOB_TOKEN registry.gitlab.eox.at

# make dirs
sudo mkdir -p /mnt/data/log
sudo mkdir -p /mnt/data/cache
sudo chown -R ubuntu:ubuntu /mnt/data

# install tools
sudo apt install -y htop

# launch docker
docker run \
  --name zone_worker \
  -e AWS_ACCESS_KEY_ID='REDACTED_API_KEY' \
  -e AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY' \
  -e MHUB_BROKER_URL='amqp://s2processor:REDACTED_API_KEY@18.197.182.82:5672//' \
  -e MHUB_RESULT_BACKEND='rpc://s2processor:REDACTED_API_KEY@18.197.182.82:5672//' \
  -e MHUB_CONFIG_DIR='/mnt/processes' \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e LOGLEVEL=$LOGLEVEL \
  -e LOGFILE=$LOGFILE \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/zone_worker:latest
