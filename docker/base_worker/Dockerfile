FROM ubuntu:16.04
MAINTAINER Joachim Ungar

ENV RASTERIO_VERSION 1.0.3.post1
ENV PROJ_VERSION=5.1.0
ENV GEOS_VERSION=3.6.2
ENV OPENJPEG_VERSION=2.3.0
ENV WEBP_VERSION=0.6.1
ENV ZSTD_VERSION=1.3.4
ENV GDAL_VERSION=2.3.1
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV C_FORCE_ROOT=True
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


# add ubuntugis-unstable repository
# install system dependencies
RUN apt -y update \
  && apt -y upgrade \
  && apt install -y software-properties-common \
  && add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable \
  && apt-get -y update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip \
  && apt update -y && apt install -y \
    git \
    libcurl4-gnutls-dev \
    libspatialindex-dev \
    libspatialite7 \
    libspatialite-dev \
    libsqlite3-dev \
    libsqlite3-mod-spatialite \
    libxerces-c-dev \
    libxerces-c-dev \
    language-pack-de \
    wget \
    cmake

# PROJ
RUN cd $APP_DIR \
   && wget -q http://download.osgeo.org/proj/proj-$PROJ_VERSION.tar.gz \
   && tar -zvxf proj-$PROJ_VERSION.tar.gz \
   && cd proj-$PROJ_VERSION \
   && ./configure CFLAGS="-O2 -Wl,-S" --prefix=$APP_DIR/local \
   && make -j8 && make install && make clean \
   && rm -rf $APP_DIR/proj-$PROJ_VERSION.tar.gz $APP_DIR/proj-$PROJ_VERSION

# GEOS
RUN cd $APP_DIR \
  && wget -q http://download.osgeo.org/geos/geos-$GEOS_VERSION.tar.bz2 \
  && tar jxf geos-$GEOS_VERSION.tar.bz2 \
  && cd geos-$GEOS_VERSION \
  && CFLAGS="-O2 -Wl,-S" CXXFLAGS="-O2 -Wl,-S" ./configure --prefix=$APP_DIR/local \
  && make -j8 && make install && make clean \
  && rm -rf $APP_DIR/geos-$GEOS_VERSION $APP_DIR/geos-$GEOS_VERSION.tar.bz2

# OPENJPEG
RUN cd $APP_DIR \
  && wget -q https://github.com/uclouvain/openjpeg/archive/v$OPENJPEG_VERSION.tar.gz \
  && tar -zvxf v$OPENJPEG_VERSION.tar.gz \
  && cd openjpeg-$OPENJPEG_VERSION/ \
  && mkdir build \
  && cd build \
  && cmake .. -DBUILD_THIRDPARTY:BOOL=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$APP_DIR/local \
  && make -j8 install && make clean \
  && rm -rf $APP_DIR/openjpeg-$OPENJPEG_VERSION $APP_DIR/v$OPENJPEG_VERSION.tar.gz

# WEBP
RUN cd $APP_DIR\
    && wget -q https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-${WEBP_VERSION}.tar.gz \
    && tar xzf libwebp-${WEBP_VERSION}.tar.gz \
    && cd libwebp-${WEBP_VERSION} \
    && CFLAGS="-O2 -Wl,-S" ./configure --prefix=$APP_DIR/local/ \
    && make && make install && make clean \
    && rm -rf $APP_DIR/libwebp-${WEBP_VERSION} $APP_DIR/libwebp-${WEBP_VERSION}.tar.gz

# ZSTD
RUN cd $APP_DIR \
  && wget -q https://github.com/facebook/zstd/archive/v${ZSTD_VERSION}.tar.gz \
  && tar -zvxf v${ZSTD_VERSION}.tar.gz \
  && cd zstd-${ZSTD_VERSION} \
  && make PREFIX=$APP_DIR/local/ ZSTD_LEGACY_SUPPORT=0 CFLAGS=-O1 \
  && make install PREFIX=$APP_DIR/local/ ZSTD_LEGACY_SUPPORT=0 CFLAGS=-O1 \
  && make clean \
  && rm -rf $APP_DIR/v${ZSTD_VERSION}.tar.gz $APP_DIR/zstd-${ZSTD_VERSION}

ENV LD_LIBRARY_PATH=$APP_DIR/local/lib:$LD_LIBRARY_PATH
ENV PKG_CONFIG_PATH=$APP_DIR/local/lib/pkgconfig/

# GDAL
RUN cd $APP_DIR \
  && wget -q http://download.osgeo.org/gdal/$GDAL_VERSION/gdal-$GDAL_VERSION.tar.gz \
  && tar -xzvf gdal-$GDAL_VERSION.tar.gz \
  && cd gdal-$GDAL_VERSION \
  && CFLAGS="-O2 -Wl,-S" CXXFLAGS="-O2 -Wl,-S" ./configure \
      --prefix=$APP_DIR/local \
      --with-proj=$APP_DIR/local \
      --with-geos=$APP_DIR/local/bin/geos-config \
      --with-openjpeg \
      --with-webp=$APP_DIR/local \
      --with-zstd=$APP_DIR/local \
      --with-threads \
      --disable-debug \
      --with-jpeg \
      --with-hide-internal-symbols \
      --with-curl \
      --with-python \
      --with-sqlite3 \
      --with-xerces \
      --with-xml2 \
      --without-bsb \
      --without-cfitsio \
      --without-cryptopp \
      --without-ecw \
      --without-expat \
      --without-fme \
      --without-freexl \
      --without-gif \
      --without-gif \
      --without-gnm \
      --without-grass \
      --without-grib \
      --without-hdf4 \
      --without-hdf5 \
      --without-idb \
      --without-ingres \
      --without-jasper \
      --without-jp2mrsid \
      --without-kakadu \
      --without-libgrass \
      --without-libkml \
      --without-libtool \
      --without-mrf \
      --without-mrsid \
      --without-mysql \
      --without-netcdf \
      --without-odbc \
      --without-ogdi \
      --without-pcidsk \
      --without-pcraster \
      --without-pcre \
      --without-perl \
      --without-pg \
      --without-php \
      --without-png \
      --without-qhull \
      --without-sde \
    && make -j8 && make install && make clean \
    && rm -rf $APP_DIR/gdal-$GDAL_VERSION.tar.gz $APP_DIR/gdal-$GDAL_VERSION

ENV GDAL_DATA=$APP_DIR/local/share/gdal
ENV PROJ_LIB=$APP_DIR/local/share/proj
ENV GDAL_CONFIG=$APP_DIR/local/bin/gdal-config
ENV GEOS_CONFIG=$APP_DIR/local/bin/geos-config
ENV PATH=$PATH:$APP_DIR/local/bin


# get deploy key for gitlab.eox.at
##################################
RUN mkdir -p /root/.ssh
COPY id_rsa /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa \
    && ssh-keyscan gitlab.eox.at >> /root/.ssh/known_hosts


# install python packages
#########################
RUN pip install cython numpy --no-binary numpy \
  && pip install --no-binary :all: rasterio==${RASTERIO_VERSION} \
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
  && pip install GDAL==$GDAL_VERSION --global-option=build_ext --global-option="-I/usr/include/gdal" \
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
  && cp -R $ROOTDIR/src/mapchete_hub/mapchete_hub/processes /mnt/

WORKDIR $ROOTDIR/src/mapchete_hub/
ENTRYPOINT ./manage.py start_${WORKER} --loglevel=$LOGLEVEL --logfile=$LOGFILE
