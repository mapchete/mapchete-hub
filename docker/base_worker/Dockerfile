FROM registry.gitlab.eox.at/maps/docker-base/gdal:latest
MAINTAINER Joachim Ungar

ENV RASTERIO_VERSION=1.0.9
ENV FIONA_VERSION=1.8.rc1
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

RUN apt -y install git \
    && rm -rf /var/lib/apt/lists/*

# install python packages
#########################
RUN pip install cython numpy boto3==1.7.32 --no-binary numpy \
  && pip install "rasterio==$RASTERIO_VERSION" "fiona==$FIONA_VERSION" --no-binary :all: \
  && pip install --upgrade setuptools \
  && git clone https://github.com/ungarj/mapchete.git \
  && cd mapchete \
  && git checkout $MAPCHETE_VERSION \
  && pip install -r requirements.txt \
  && python setup.py develop \
  && cd $ROOTDIR/src \
  && git clone http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git \
  && cd orgonite \
  && git chekout $ORGONITE_VERSION \
  && pip install -r requirements.txt \
  && python setup.py build_ext --inplace \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  && git clone http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git \
  && cd mapchete_satellite \
  && git checkout $MAPCHETE_SATELLITE_VERSION \
  && pip install -r requirements.txt -r requirements_aws.txt -r requirements_mundi.txt -r requirements_test.txt \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  && git clone http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git \
  && cd mapchete_hub  \
  && git checkout $MAPCHETE_HUB_VERSION \
  && pip install -r requirements.txt -r requirements_test.txt \
  && python setup.py install \
  && python setup.py test

WORKDIR $ROOTDIR/src/mapchete_hub
ENTRYPOINT ./manage.py start-`echo $WORKER | sed s/_/-/g` --loglevel=$LOGLEVEL --logfile=$LOGFILE
