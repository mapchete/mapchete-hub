#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

This script prints base64 encoded output of generate_user_data.sh inserted into spot_config_skeleton.json.

Parameters:
    -h   Show this help text and exit.
    -t   Instance type. (default: m5dn.2xlarge)
    -z   Zone to launch instances into. (default: eu-central-1a)
    -b   Block spot duration in minutes. Must be a multiple of 60. A value of 0 won't trigger a block request. (default: 0)
"

while getopts z:b:t: option
    do
        case "${option}"
        in
            z) AVAILABILITY_ZONE=${OPTARG};;
            b) BLOCK_DURATION=${OPTARG};;
            t) INSTANCE_TYPE=${OPTARG};;
        esac
    done
AVAILABILITY_ZONE=${AVAILABILITY_ZONE:-"eu-central-1a"}
BLOCK_DURATION=${BLOCK_DURATION:-0}
INSTANCE_TYPE=${INSTANCE_TYPE:-"m5dn.2xlarge"}

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

if [ ! -f ".env" ]; then
    echo "no .env file found"
    exit 0
fi;

if [ "$BLOCK_DURATION" == 0 ]; then
    sed "s/USER_DATA/$(./generate_user_data.sh base64)/g; \
        s/AVAILABILITY_ZONE/${AVAILABILITY_ZONE}/g; \
        /BLOCK_DURATION/d; \
        s/INSTANCE_TYPE/${INSTANCE_TYPE}/g;" skeletons/spot_config_skeleton.json
else
    sed "s/USER_DATA/$(./generate_user_data.sh base64)/g; \
        s/AVAILABILITY_ZONE/${AVAILABILITY_ZONE}/g; \
        s/BLOCK_DURATION/${BLOCK_DURATION}/g; \
        s/INSTANCE_TYPE/${INSTANCE_TYPE}/g;" skeletons/spot_config_skeleton.json
fi
