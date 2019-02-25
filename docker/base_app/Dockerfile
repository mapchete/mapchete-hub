FROM registry.gitlab.eox.at/maps/docker-base/gdal:latest
MAINTAINER Joachim Ungar

ENV RASTERIO_VERSION=1.0.13
ENV FIONA_VERSION=1.8.4
ENV BOTO3_VESION=1.7.32
ENV MAPCHETE_VERSION=master
ENV ORGONITE_VERSION=master
ENV MAPCHETE_SATELLITE_VERSION=master
ENV MAPCHETE_HUB_VERSION=master
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
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
RUN pip install cython numpy "boto3==$BOTO3_VESION" --no-binary numpy \
  && pip install "rasterio==$RASTERIO_VERSION" "fiona==$FIONA_VERSION" --no-binary :all: \
  && pip install --upgrade setuptools \
  # mapchete
  && git clone https://github.com/ungarj/mapchete.git \
  && cd mapchete \
  && git checkout $MAPCHETE_VERSION \
  && pip install -r requirements.txt \
  && python setup.py develop \
  && cd $ROOTDIR/src \
  # mapchete_hub
  && git clone http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git \
  && cd mapchete_hub  \
  && git checkout $MAPCHETE_HUB_VERSION \
  && pip install -r requirements.txt -r requirements_test.txt \
  && python setup.py install \
  && python setup.py test

WORKDIR $ROOTDIR/src/mapchete_hub/
ENTRYPOINT ./manage.py $SUBCOMMAND --loglevel=$LOGLEVEL --logfile=$LOGFILE
