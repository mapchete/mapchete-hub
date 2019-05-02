FROM registry.gitlab.eox.at/maps/docker-base/snap-mapchete:latest
MAINTAINER Joachim Ungar

ENV MAPCHETE_HUB_VERSION=master
ENV ORGONITE_VERSION=master
ENV METIS_VERSION=master
ENV MAPCHETE_SATELLITE_VERSION=master
ENV AWS_REQUEST_PAYER=requester
ENV ROOTDIR=/usr/local
ENV APP_DIR=/tmp/app

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

ARG AWS_S3_ENDPOINT
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG MHUB_BROKER_URL
ARG MHUB_RESULT_BACKEND
ARG WORKER

RUN apt update -y \
  && apt install -y libspatialindex-dev \
  && rm -rf /var/lib/apt/lists/*

# install python packages
#########################
RUN pip install git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@${ORGONITE_VERSION}#egg=orgonite && \
  pip install git+http://gitlab+deploy-token-6:_AHLpsvzLQq3j4a_w95R@gitlab.eox.at/maps/metis.git@${METIS_VERSION}#egg=metis && \
  pip install -e git+http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git@${MAPCHETE_HUB_VERSION}#egg=mapchete_hub[mundi] --src ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}

WORKDIR ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}/mapchete-hub
ENTRYPOINT ./manage.py start-`echo $WORKER | sed s/_/-/g` --loglevel=$LOGLEVEL --logfile=$LOGFILE
