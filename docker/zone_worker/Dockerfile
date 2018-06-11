FROM ubuntu:16.04
MAINTAINER Joachim Ungar

ENV ROOTDIR /usr/local
ENV RASTERIO_VERSION 1.0b1

WORKDIR $ROOTDIR/src

# add ubuntugis-unstable repository
RUN apt -y update \
  && apt -y upgrade \
  && apt install -y software-properties-common \
  && add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable \
  && apt-get -y update

# python 3
RUN apt-get install -y python3-pip python3-dev\
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

RUN apt update -y && apt install -y \
    git \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libspatialite7 \
    libspatialite-dev \
    libsqlite3-mod-spatialite \
    language-pack-de

# strange fix for remote rasters
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# install NumPy & rasterio
##########################
RUN pip install --no-binary :all: numpy \
  && pip install rasterio==${RASTERIO_VERSION}

# install latest mapchete
#########################
# RUN pip install mapchete
RUN git clone https://github.com/ungarj/mapchete.git \
    && cd mapchete \
    && pip install -r requirements.txt \
    && python setup.py develop

# get deploy key for gitlab.eox.at
##################################
RUN mkdir -p /root/.ssh
COPY id_rsa /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa \
    && ssh-keyscan gitlab.eox.at >> /root/.ssh/known_hosts


# install orgonite, mapchete-s2aws & mapchete-s3
################################################
RUN pip install --upgrade setuptools
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

# orgonite
RUN git clone git@gitlab.eox.at:maps/orgonite.git \
    && cd orgonite \
    && pip install -r requirements.txt \
    && python setup.py build_ext --inplace \
    && python setup.py develop \
    && python setup.py test \
    && cd ..

# mapchete-s2aws
RUN git clone git@gitlab.eox.at:maps/mapchete_s2aws.git \
    && cd mapchete_s2aws \
    && pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal" \
    && pip install -r requirements.txt \
    && python setup.py develop \
    && python setup.py test \
    && cd ..

# mapchete-s3
RUN git clone https://github.com/ungarj/mapchete-s3.git \
    && cd mapchete-s3 \
    && pip install -r requirements.txt \
    && python setup.py develop \
    && python setup.py test

# mapchete hub
##############
RUN git clone git@gitlab.eox.at:maps/mapchete_hub.git \
    && cd mapchete_hub  \
    && pip install -r requirements.txt \
    && python setup.py install \
    # && python setup.py test \
    && cd ..

# clean up
RUN rm /root/.ssh/id_rsa

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN mkdir /mnt/data
WORKDIR $ROOTDIR/src/mapchete_hub/
ENTRYPOINT ./manage.py start_zone_worker --loglevel=$LOGLEVEL --logfile=$LOGFILE
