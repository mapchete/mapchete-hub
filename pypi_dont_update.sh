#!/bin/bash

# pip list --format=freeze | grep "rasterio fiona"

echo ""
for PACKAGE in $@; do
    RESULTS=`pip list --format=freeze | grep -i "${PACKAGE}=="`
    for RESULT in ${RESULTS}; do
        echo ${RESULT}
    done
done