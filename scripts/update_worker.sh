#!/bin/bash

# Use this script is in zone_worker instances.

docker container stop zone_worker
rm -f /mnt/data/cache/*

# log into registry
CI_JOB_TOKEN=REDACTED_API_KEY
docker login -u gitlab-ci-token -p $CI_JOB_TOKEN registry.gitlab.eox.at
docker pull registry.gitlab.eox.at/maps/mapchete_hub/base_worker:latest

# set environment and run container
LOGLEVEL='INFO'
LOGFILE=/mnt/data/log/worker.log
AWS_ACCESS_KEY_ID='REDACTED_API_KEY'
AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY'
MHUB_BROKER_URL='amqp://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_RESULT_BACKEND='rpc://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_CONFIG_DIR='/mnt/processes'
WORKER='zone_worker'
docker run \
  --rm \
  --name $WORKER \
  -e WORKER=$WORKER \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
  -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
  -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
  -e MPS2AWS_CACHE_PATH=/mnt/data/cache \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
  -e LOGLEVEL=$LOGLEVEL \
  -e LOGFILE=$LOGFILE \
  -v /mnt/data:/mnt/data \
  -d \
  registry.gitlab.eox.at/maps/mapchete_hub/base_worker:latest
