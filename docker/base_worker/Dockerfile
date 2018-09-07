FROM ubuntu:16.04
MAINTAINER Joachim Ungar

ENV ROOTDIR /usr/local
ENV RASTERIO_VERSION 1.0.2
# strange fix for remote rasters
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
# set lang variables & allow celery to run as root
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV C_FORCE_ROOT True
# set AWS request payer variable
ENV AWS_REQUEST_PAYER=requester

WORKDIR $ROOTDIR/src

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG MHUB_BROKER_URL
ARG MHUB_RESULT_BACKEND
ARG WORKER


# add ubuntugis-unstable repository
# install system dependencies
RUN apt -y update \
  && apt -y upgrade \
  && apt install -y software-properties-common \
  && add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable \
  && apt-get -y update \
  && apt-get install -y python3-pip python3-dev\
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip \
  && apt update -y && apt install -y \
    git \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libspatialite7 \
    libspatialite-dev \
    libsqlite3-mod-spatialite \
    language-pack-de

# get deploy key for gitlab.eox.at
##################################
RUN mkdir -p /root/.ssh
COPY id_rsa /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa \
    && ssh-keyscan gitlab.eox.at >> /root/.ssh/known_hosts

# install NumPy & rasterio
##########################
RUN pip install --no-binary :all: numpy \
  && pip install rasterio==${RASTERIO_VERSION} \
  && pip install --upgrade setuptools \
  && git clone https://github.com/ungarj/mapchete.git \
  && cd mapchete \
  && pip install -r requirements.txt \
  && python setup.py develop \
  && cd $ROOTDIR/src \
  && git clone git@gitlab.eox.at:maps/orgonite.git \
  && cd orgonite \
  && pip install -r requirements.txt \
  && git checkout L1C-masks_final \
  && python setup.py build_ext --inplace \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  && git clone git@gitlab.eox.at:maps/mapchete_s2aws.git \
  && cd mapchete_s2aws \
  && pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal" \
  && pip install -r requirements.txt \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  && git clone https://github.com/ungarj/mapchete-s3.git \
  && cd mapchete-s3 \
  && pip install -r requirements.txt \
  && python setup.py develop \
  && python setup.py test \
  && cd $ROOTDIR/src \
  && git clone git@gitlab.eox.at:maps/mapchete_hub.git \
  && cd mapchete_hub  \
  && pip install -r requirements.txt \
  && python setup.py install \
  && cd $ROOTDIR/src \
  # && python setup.py test \
  && rm /root/.ssh/id_rsa \
  && cp -R $ROOTDIR/src/mapchete_hub/processes /mnt/

WORKDIR $ROOTDIR/src/mapchete_hub/
ENTRYPOINT ./manage.py start_${WORKER} --loglevel=$LOGLEVEL --logfile=$LOGFILE
