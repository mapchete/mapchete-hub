# use builder to build python wheels #
######################################
ARG BASE_IMAGE_NAME=mapchete
ARG BASE_IMAGE_TAG=0.7
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} as builder
MAINTAINER Joachim Ungar

ENV MAPCHETE_SATELLITE_VERSION 0.8
ENV ORGONITE_VERSION 0.5
ENV EOX_PREPROCESSING_VERSION 0.10

ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV WHEEL_DIR /usr/local/wheels

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p $MHUB_DIR
RUN pip install cython \
    && pip wheel \
        git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@${MAPCHETE_SATELLITE_VERSION} \
        git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@${ORGONITE_VERSION} \
        git+http://gitlab+deploy-token-9:91czUKTs2wF2-UpcDcMG@gitlab.eox.at/maps/preprocessing.git@${EOX_PREPROCESSING_VERSION} \
        --wheel-dir $WHEEL_DIR \
        --no-deps

RUN pip wheel \
        boto3>=1.13.4 \
        botocore>=1.16.4 \
        godale \
        gunicorn==19.9.0 \
        jenkspy \
        mapchete_xarray \
        numcodecs==0.6.4 \
        psutil \
        xarray \
        --wheel-dir $WHEEL_DIR \
        --no-deps


# build image using pre-built libraries and wheels #
####################################################
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} as runner
MAINTAINER Joachim Ungar

ENV AWS_REQUEST_PAYER requester
ENV C_FORCE_ROOT "yes"
ENV GML_SKIP_CORRUPTED_FEATURES YES
ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV WHEEL_DIR /usr/local/wheels

# get and install wheels from builder
COPY --from=builder $WHEEL_DIR $WHEEL_DIR
RUN pip install \
        $WHEEL_DIR/jenkspy*.whl \
        $WHEEL_DIR/orgonite*.whl \
        $WHEEL_DIR/psutil*.whl \
        $WHEEL_DIR/mapchete_satellite*.whl \
        $WHEEL_DIR/*.whl \
    && rm $WHEEL_DIR/*

# get dependencies before checking out source code to speed up container build
COPY requirements.txt $MHUB_DIR/
RUN pip install -r $MHUB_DIR/requirements.txt

# copy mapchete_hub source code and install
COPY . $MHUB_DIR
RUN pip install -e $MHUB_DIR[complete]

WORKDIR $MHUB_DIR
