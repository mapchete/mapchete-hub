FROM registry.gitlab.eox.at/maps/docker-base/snap-mapchete:latest
MAINTAINER Joachim Ungar

ENV MAPCHETE_VERSION=master
ENV ORGONITE_VERSION=0.3
ENV METIS_VERSION=0.1
ENV MAPCHETE_SATELLITE_VERSION=master
ENV MAPCHETE_HUB_VERSION=master
ENV AWS_REQUEST_PAYER=requester
ENV ROOTDIR=/usr/local
ENV APP_DIR=/tmp/app

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

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
  # orgonite
RUN git clone http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git \
  && cd orgonite \
  && git checkout $ORGONITE_VERSION \
  && pip install -r requirements.txt \
  && python setup.py build_ext --inplace \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  # mapchete_satellite
  && git clone http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git \
  && cd mapchete_satellite \
  && git checkout $MAPCHETE_SATELLITE_VERSION \
  && pip install -r requirements.txt -r requirements_cli.txt -r requirements_mundi.txt -r requirements_s1.txt -r requirements_test.txt\
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  # metis
  && git clone http://gitlab+deploy-token-6:_AHLpsvzLQq3j4a_w95R@gitlab.eox.at/maps/metis.git \
  && cd metis \
  && git checkout $METIS_VERSION \
  && pip install -r requirements.txt -r requirements_tests.txt \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  # mapchete_hub
  && git clone http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git \
  && cd mapchete_hub  \
  && git checkout $MAPCHETE_HUB_VERSION \
  && pip install -r requirements.txt -r requirements_test.txt \
  && python setup.py install \
  && python setup.py test

WORKDIR $ROOTDIR/src/mapchete_hub
ENTRYPOINT ./manage.py start-`echo $WORKER | sed s/_/-/g` --loglevel=$LOGLEVEL --logfile=$LOGFILE
