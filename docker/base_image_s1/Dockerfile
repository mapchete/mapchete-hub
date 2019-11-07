FROM registry.gitlab.eox.at/maps/docker-base/snap-mapchete:0.2
MAINTAINER Joachim Ungar

ENV MAPCHETE_HUB_VERSION 0.2
ENV MAPCHETE_SATELLITE_VERSION 0.3
ENV AWS_REQUEST_PAYER requester
ENV ROOTDIR /usr/local
ENV APP_DIR /tmp/app
ENV C_FORCE_ROOT "yes"
ENV GML_SKIP_CORRUPTED_FEATURES YES

RUN mkdir $APP_DIR
WORKDIR $ROOTDIR/src

# install python packages
#########################
RUN pip install -e git+http://gitlab+deploy-token-3:SV2HivQ_xiKVxSVEtYCr@gitlab.eox.at/maps/mapchete_satellite.git@${MAPCHETE_SATELLITE_VERSION}#egg=mapchete_satellite[xarray] && \
  pip install -e git+http://gitlab+deploy-token-5:Yz84UvRWVVG7K7e6u7n_@gitlab.eox.at/maps/mapchete_hub.git@${MAPCHETE_HUB_VERSION}#egg=mapchete_hub[mundi] --src ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}

WORKDIR ${ROOTDIR}/src/mapchete_hub/${MAPCHETE_HUB_VERSION}/mapchete-hub
