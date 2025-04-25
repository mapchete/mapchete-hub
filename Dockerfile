ARG BASE_IMAGE_NAME=mapchete
ARG BASE_IMAGE_TAG=2025.4.1


# use builder to build python wheels #
######################################
# NOTE:
#
# When testing other packages e.g. mapchete_satellite just uncomment line and replace
# "master" with your branch name.
#
# If your test branch needs new requirements, add them here under the following pip wheel
# command. This also applies to dependencies which require building (like jenkspy) which
# should be added here as build dependencies are not available in the runner stage.
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} AS builder
ARG EOX_PYPI_TOKEN

ENV BUILD_DIR=/usr/local
ENV MHUB_DIR=$BUILD_DIR/src/mapchete_hub

RUN apt-get update && \
    apt-get install --yes --no-install-recommends build-essential gcc g++ git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip pip-tools

# get requirements from mhub
COPY pypi_dont_update.sh $MHUB_DIR/
COPY requirements.in $MHUB_DIR/

# this is important so pip won't update our precious precompiled packages:
RUN ./$MHUB_DIR/pypi_dont_update.sh \
    affine \
    aiobotocore \
    aiohttp \
    boto3 \
    botocore \
    dask-gateway \
    dask-gateway-server \
    fiona \
    fsspec \
    GDAL \
    mapchete \
    numcodecs \
    numpy \
    psutil \
    rasterio \
    shapely \
    snuggs \
    s3fs \
    tblib \
    tqdm \
    tilematrix \
    zipp \
    >> ${MHUB_DIR}/requirements.in
RUN cat $MHUB_DIR/requirements.in
RUN pip-compile \
    -v \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    $MHUB_DIR/requirements.in -o $MHUB_DIR/combined_requirements.txt
RUN cat $MHUB_DIR/combined_requirements.txt

# build image using pre-built libraries and wheels #
####################################################
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} AS runner
ARG BASE_IMAGE_NAME
ARG EOX_PYPI_TOKEN

ENV C_FORCE_ROOT="yes"
ENV GML_SKIP_CORRUPTED_FEATURES=YES
ENV BUILD_DIR=/usr/local
ENV MHUB_DIR=$BUILD_DIR/src/mapchete_hub

RUN apt-get update && \
    apt-get install --yes htop && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder $MHUB_DIR/combined_requirements.txt $MHUB_DIR/combined_requirements.txt

RUN pip install \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    -r $MHUB_DIR/combined_requirements.txt

# copy mapchete_hub source code and install
COPY . $MHUB_DIR

RUN pip install -e $MHUB_DIR[complete]

WORKDIR $MHUB_DIR
