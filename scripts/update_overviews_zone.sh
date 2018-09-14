#!/bin/bash

# Use this script in joker machine.

zoom=$1
row=$2
col=$3

zone="$zoom $row $col"
index_mapchete="overviews.mapchete"
index_path="/mnt/data/indexes/"

mapchete execute $index_mapchete --verbose -m 8 -b `tmx bounds $zone` -z 8,12 -o && \
mapchete index $index_mapchete --verbose --shp --for_gdal --out_dir $index_path -b `tmx bounds $zone` -z 8,13
