#!/bin/bash

# usage:
# source alias_mapcache_seed.sh

LOCAL_VOLUME_DIR=${LOCAL_VOLUME_DIR:-"/mnt/data"}
MAPCACHE_IMAGE_TAG="latest"

# create mapcache_seed alias
MAPCACHE_SEED_CMD="docker run \
  --rm \
  -it \
  --name=mapcache_seed \
  -v ${LOCAL_VOLUME_DIR}/caches:/var/sig/tiles \
  -v ${LOCAL_VOLUME_DIR}/config:/etc/mapcache/ \
  registry.gitlab.eox.at/maps/docker-base/mapcache:${MAPCACHE_IMAGE_TAG} \
  mapcache_seed --config /etc/mapcache/mapcache.xml"
alias mapcache_seed=$(echo $MAPCACHE_SEED_CMD)
