FROM registry.gitlab.eox.at/maps/docker-base/snap-mapchete:latest
MAINTAINER Joachim Ungar

ENV EOX_PREPROCESSING_VERSION=master
ENV MAPCHETE_HUB_VERSION=master
ENV ORGONITE_VERSION=master
ENV METIS_VERSION=master
ENV MAPCHETE_SATELLITE_VERSION=master
ENV AWS_REQUEST_PAYER=requester
ENV ROOTDIR=/usr/local
ENV APP_DIR=/tmp/app
ENV C_FORCE_ROOT=True

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

ARG AWS_S3_ENDPOINT
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
  pip install git+http://gitlab+deploy-token-6:_AHLpsvzLQq3j4a_w95R@gitlab.eox.at/maps/metis.git@${METIS_VERSION}#egg=metis && \
  pip install git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@${MAPCHETE_SATELLITE_VERSION}#egg=mapchete_satellite && \
  pip install -e git+http://gitlab+deploy-token-9:91czUKTs2wF2-UpcDcMG@gitlab.eox.at/maps/preprocessing.git@${EOX_PREPROCESSING_VERSION}#egg=eox_preprocessing && \
  cd ${ROOTDIR}/src && \
  git clone http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git && \
  cd mapchete_hub && \
  git checkout ${MAPCHETE_HUB_VERSION} && \
  pip install -e .[mundi]

WORKDIR ${ROOTDIR}/src/mapchete_hub
ENTRYPOINT ./manage.py worker --loglevel=$LOGLEVEL
