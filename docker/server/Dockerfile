FROM registry.gitlab.eox.at/maps/docker-base/mapchete:latest
MAINTAINER Joachim Ungar

ENV MAPCHETE_HUB_VERSION=master
ENV AWS_REQUEST_PAYER=requester
ENV ROOTDIR=/usr/local
ENV APP_DIR=/tmp/app

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG LOGFILE
ARG LOGLEVEL
ARG MHUB_BROKER_URL
ARG MHUB_RESULT_BACKEND

# install python packages
#########################
RUN pip install -e git+http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git@${MAPCHETE_HUB_VERSION}#egg=mapchete_hub --src ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION} \
    && pip install gunicorn

WORKDIR ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}/mapchete-hub
ENTRYPOINT gunicorn --bind 0.0.0.0:5000 --log-level $LOGLEVEL -w 1 "mapchete_hub.application:flask_app(monitor=True)"
