FROM registry.gitlab.eox.at/maps/docker-base/mapchete:latest
MAINTAINER Joachim Ungar

ENV MAPCHETE_HUB_VERSION=master
ENV ORGONITE_VERSION=master
ENV MAPCHETE_SATELLITE_VERSION=master
ENV AWS_REQUEST_PAYER=requester
ENV ROOTDIR=/usr/local
ENV APP_DIR=/tmp/app
ENV C_FORCE_ROOT="yes"

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG LOGLEVEL
ARG MHUB_BROKER_URL
ARG MHUB_RESULT_BACKEND
ARG WORKER
ARG QUEUE

# install python packages
#########################
RUN pip install git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@${ORGONITE_VERSION}#egg=orgonite && \
  pip install -e git+http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git@${MAPCHETE_HUB_VERSION}#egg=mapchete_hub[mundi] --src ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}

WORKDIR ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}/mapchete-hub
ENTRYPOINT ./manage.py worker -n $WORKER -q $QUEUE --loglevel=$LOGLEVEL
