FROM registry.gitlab.eox.at/maps/docker-base/mapchete:0.2
MAINTAINER Joachim Ungar

ENV AWS_REQUEST_PAYER=requester
ENV C_FORCE_ROOT="yes"
ENV GML_SKIP_CORRUPTED_FEATURES=YES
ENV MHUB_DIR=$ROOTDIR/src/mapchete_hub
ENV ROOTDIR=/usr/local

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG GUNICORN_CMD_ARGS
ARG LOGLEVEL
ARG MHUB_BROKER_URL
ARG MHUB_CELERY_SLACK
ARG MHUB_CONFIG_DIR
ARG MHUB_INDEX_OUTPUT_DIR
ARG MHUB_RESULT_BACKEND
ARG MHUB_STATUS_GPKG
ARG MHUB_QUEUE
ARG MHUB_WORKER
ARG MP_SATELLITE_CACHE_PATH
ARG SLACK_WEBHOOK_URL

RUN mkdir -p $MHUB_DIR

# install dependencies before checking out source code to speed up container build
COPY requirements.txt $MHUB_DIR/
RUN pip install gunicorn==19.9.0 xarray -r $MHUB_DIR/requirements.txt

# copy mapchete_hub source code and install
COPY . $MHUB_DIR
RUN pip install -e $MHUB_DIR

WORKDIR $MHUB_DIR
