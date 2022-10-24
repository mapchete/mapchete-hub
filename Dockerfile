ARG BASE_IMAGE_NAME=mapchete
ARG BASE_IMAGE_TAG=curl_7.85.0

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
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} as builder
ARG EOX_PYPI_TOKEN

ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV WHEEL_DIR /usr/local/wheels

RUN apt-get update && \
    apt-get install --yes --no-install-recommends build-essential gcc g++ git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

RUN mkdir -p $MHUB_DIR $WHEEL_DIR

# Build wheels either for packages which need to always be built or for packages which are
# under current development and where a specific branch is required.
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    # git+https://github.com/ungarj/mapchete.git@master \
    # git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@master \
    # git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@master \
    # git+http://gitlab+deploy-token-9:91czUKTs2wF2-UpcDcMG@gitlab.eox.at/maps/preprocessing.git@0.10 \
    # git+http://gitlab+deploy-token-84:x-16dE-pd2ENHpmBiJf1@gitlab.eox.at/maps/s2brdf.git@master \
    # git+http://gitlab+deploy-token-114:Z5BGRFqisidtaryTcJoe@gitlab.eox.at/eox/hub/agri/planet-signals-generation.git@master \
    # git+https://github.com/wankoelias/mapchete_xarray.git@master \
    # git+https://github.com/dask/distributed.git@master \
    # git+https://github.com/dask/dask.git@master \
    jenkspy==0.2.0 \
    --wheel-dir $WHEEL_DIR \
    --no-deps

# build image using pre-built libraries and wheels #
####################################################
FROM registry.gitlab.eox.at/maps/docker-base/${BASE_IMAGE_NAME}:${BASE_IMAGE_TAG} as runner
ARG BASE_IMAGE_NAME
ARG EOX_PYPI_TOKEN

ENV C_FORCE_ROOT "yes"
ENV GML_SKIP_CORRUPTED_FEATURES YES
ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV MP_SATELLITE_REMOTE_TIMEOUT=30
ENV WHEEL_DIR /usr/local/wheels

# get wheels from builder
COPY --from=builder $WHEEL_DIR $WHEEL_DIR
# get requirements from mhub
COPY pypi_dont_update.sh $MHUB_DIR/
COPY requirements.in $MHUB_DIR/

# install wheels first and then everything else
RUN pip install --upgrade pip && \
    pip install \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    $WHEEL_DIR/*.whl && \
    # this is important so pip won't update our precious precompiled packages:
    ./$MHUB_DIR/pypi_dont_update.sh \
    dask-gateway \
    dask-gateway-server \
    affine \
    aiohttp \
    boto3 \
    botocore \
    fiona \
    fsspec \
    gdal \
    jenkspy \
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
    >> ${MHUB_DIR}/requirements.in && \
    cat $MHUB_DIR/requirements.in && \
    pip install pip-tools && \
    pip-compile \
    -v \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    $MHUB_DIR/requirements.in -o $MHUB_DIR/requirements.txt && \
    pip install \
    --extra-index-url https://__token__:${EOX_PYPI_TOKEN}@gitlab.eox.at/api/v4/projects/255/packages/pypi/simple \
    -r $MHUB_DIR/requirements.txt && \
    pip uninstall -y pip-tools && \
    rm -r $WHEEL_DIR

# copy mapchete_hub source code and install
COPY . $MHUB_DIR

# install xarray dependencies only on mhub image, not mhub-s1
RUN if [ "$BASE_IMAGE_NAME" = "mapchete" ]; \
    then pip install -e $MHUB_DIR[slack,xarray]; \
    else pip install -e $MHUB_DIR[slack]; \
    fi

WORKDIR $MHUB_DIR
