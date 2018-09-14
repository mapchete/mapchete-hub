#!/bin/bash

# Use this script in joker machine.

lon=$1
lat=$2
point="$lon $lat"

bounds=`tmx -m 4 bounds -- \`tmx -m 4 tile -- 13 $point\``
execute_mapchete="mosaic_north_nocache.mapchete"
index_mapchete="overviews.mapchete"
index_path="/mnt/data/indexes/"

mapchete execute $execute_mapchete --verbose --logfile missing.log -m 8 -b $bounds -z 8,13 -o -d && \
mapchete index $index_mapchete --verbose --shp --for_gdal --out_dir $index_path -b $bounds -z 8,13
