# use builder to build python wheels #
######################################
ARG BASE_IMAGE_NAME=mapchete
ARG BASE_IMAGE_TAG=0.13
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} as builder
MAINTAINER Joachim Ungar

ARG EOX_PYPI_TOKEN
# ENV MAPCHETE_SATELLITE_VERSION 0.11
ENV EOX_PREPROCESSING_VERSION 0.10
# ENV ORGONITE_VERSION 0.6
# ENV S2BRDF_VERSION 0.6

ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV WHEEL_DIR /usr/local/wheels

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p $MHUB_DIR
COPY requirements.txt $MHUB_DIR/
RUN pip wheel --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
        -r $MHUB_DIR/requirements.txt \
        # git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@${MAPCHETE_SATELLITE_VERSION} \
        # git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@${ORGONITE_VERSION} \
        git+http://gitlab+deploy-token-9:91czUKTs2wF2-UpcDcMG@gitlab.eox.at/maps/preprocessing.git@${EOX_PREPROCESSING_VERSION} \
        # git+http://gitlab+deploy-token-84:x-16dE-pd2ENHpmBiJf1@gitlab.eox.at/maps/s2brdf.git@${S2BRDF_VERSION} \
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
ENV MAPCHETE_SATELLITE_VERSION 0.11
ENV MP_SATELLITE_REMOTE_TIMEOUT=30
ENV ORGONITE_VERSION 0.6
ENV WHEEL_DIR /usr/local/wheels

# get wheels from builder
COPY --from=builder $WHEEL_DIR $WHEEL_DIR
RUN pip install --upgrade pip && \
    pip install $WHEEL_DIR/*.whl && \
    rm $WHEEL_DIR/* && \
    pip install boto3 botocore pystac pytz --upgrade --use-feature=2020-resolver

# copy mapchete_hub source code and install
COPY . $MHUB_DIR
RUN pip install -e $MHUB_DIR[complete]

WORKDIR $MHUB_DIR
