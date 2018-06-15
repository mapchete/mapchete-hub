#!/bin/bash

CI_JOB_TOKEN=REDACTED_API_KEY
AWS_ACCESS_KEY_ID='REDACTED_API_KEY'
AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY'
MHUB_BROKER_URL='amqp://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_RESULT_BACKEND='rpc://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_CONFIG_DIR='/mnt/processes'
INDEX_OUTPUT_DIR='/mnt/data/indexes'
PREVIEW_PERMALINK='http://18.185.13.154/'
SLACK_WEBHOOK_URL='REDACTED_API_KEY'
LOGLEVEL='DEBUG'
LOGFILE='/mnt/data/log/preview_worker.log'


# install docker
curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
sudo chmod g+rwx "/home/$USER/.docker" -R

# get rgb_worker docker container
docker login -u gitlab-ci-token -p $CI_JOB_TOKEN registry.gitlab.eox.at

# make dirs
sudo mkdir -p /mnt/data/log
sudo mkdir -p /mnt/data/indexes
sudo mkdir -p /mnt/data/map/html
# TODO: copy mapfile into /mnt/data/map and index.html into /mnt/data/map/html
sudo chown -R ubuntu:ubuntu /mnt/data

# install tools
sudo apt install -y htop

# launch mapserver container
docker run \
  --rm \
  --name=mapserver \
  -p 80:80 \
  -v /mnt/data/map/html:/var/www/html \
  -v /mnt/data/map:/map \
  -v /mnt/data/indexes:/indexes \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/mapserver

# launch preview_worker container
docker run \
  --rm \
  --name preview_worker \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e INDEX_OUTPUT_DIR=$INDEX_OUTPUT_DIR \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -e LOGLEVEL=$LOGLEVEL \
  -e LOGFILE=$LOGFILE \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/preview_worker:latest
