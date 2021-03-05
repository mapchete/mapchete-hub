#!/bin/bash

# pip list --format=freeze | grep "rasterio fiona"

echo ""
for PACKAGE in $@; do
    echo `pip list --format=freeze | grep -i ${PACKAGE}`
done