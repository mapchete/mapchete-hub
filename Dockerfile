# use builder to build python wheels #
######################################
FROM registry.gitlab.eox.at/maps/docker-base/mapchete:0.5 as builder
MAINTAINER Joachim Ungar

ENV GODALE_VERSION 0.2
ENV MAPCHETE_SATELLITE_VERSION 0.4
ENV ORGONITE_VERSION 0.5

ENV BUILD_DIR /usr/local
ENV MHUB_DIR $BUILD_DIR/src/mapchete_hub
ENV WHEEL_DIR /usr/local/wheels

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential gcc git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p $MHUB_DIR

# get dependencies before checking out source code to speed up container build
COPY requirements.txt $MHUB_DIR/
RUN pip install cython numpy \
    && pip wheel \
        git+http://gitlab+deploy-token-7:3AFUNqdLiKayR9Ang9Gx@gitlab.eox.at/maps/godale.git@${GODALE_VERSION} \
        gunicorn==19.9.0 \
        jenkspy \
        git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@${MAPCHETE_SATELLITE_VERSION} \
        git+http://gitlab+deploy-token-4:9wY1xu44PggPQKZLmNxj@gitlab.eox.at/maps/orgonite.git@${ORGONITE_VERSION} \
        psutil \
        xarray \
        -r $MHUB_DIR/requirements.txt --wheel-dir $WHEEL_DIR --no-deps \
    && pip wheel GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal" --wheel-dir $WHEEL_DIR \
    && pip uninstall --yes cython

# build image using pre-built libraries and wheels #
####################################################
FROM registry.gitlab.eox.at/maps/docker-base/mapchete:0.5 as final
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
        $WHEEL_DIR/godale*.whl \
        $WHEEL_DIR/psutil*.whl \
        $WHEEL_DIR/mapchete_satellite*.whl \
        $WHEEL_DIR/*.whl \
    && rm $WHEEL_DIR/*

# copy mapchete_hub source code and install
COPY . $MHUB_DIR
RUN pip install -e $MHUB_DIR

WORKDIR $MHUB_DIR
