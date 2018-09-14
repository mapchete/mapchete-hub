#!/bin/bash

# Use this script on the preview_worker instance.

# set environment and run containers
AWS_ACCESS_KEY_ID='REDACTED_API_KEY'
AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY'
MHUB_BROKER_URL='amqp://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_RESULT_BACKEND='rpc://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
MHUB_CONFIG_DIR='/mnt/processes'
INDEX_OUTPUT_DIR='/mnt/data/indexes'
HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
PREVIEW_PERMALINK='http://'$HOST_IP
SLACK_WEBHOOK_URL='REDACTED_API_KEY'
LOGLEVEL='DEBUG'
LOGFILE='/mnt/data/log/preview_worker.log'
WORKER='preview_worker'
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
  registry.gitlab.eox.at/maps/mapchete_hub/mapserver:latest
docker run \
  --rm \
  --name $WORKER \
  -e WORKER=$WORKER \
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
  registry.gitlab.eox.at/maps/mapchete_hub/base_worker:latest
