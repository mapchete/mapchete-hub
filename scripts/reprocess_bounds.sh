#!/bin/bash

# Use this script in joker machine.

left=$1
bottom=$2
right=$3
top=$4

bounds="$left $bottom $right $top"
execute_mapchete="mosaic_north_nocache.mapchete"
index_mapchete="overviews.mapchete"
index_path="/mnt/data/indexes/"

mapchete execute $execute_mapchete --verbose -m 8 -b $bounds -z 8,13 -o && \
mapchete index $index_mapchete --verbose --shp --for_gdal --out_dir $index_path -b $bounds -z 8,13
