#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

This script prints base64 encoded output of generate_user_data.sh inserted into spot_config_skeleton.json.

Parameters:
    -h                      Show this help text and exit.
    --instance-type         Instance type. (default: m5dn.2xlarge)
    --availability-zone     Zone to launch instances into. (default: eu-central-1a)
    --volume-size           Size of additional volume in GB. (default: 150)
    --image, -i             Image to be used. (either mhub or mhub-s1) (default: mhub)
    --tag, -t               Tag used for mhub image. (default: stable)
"

while [ $# -gt 0 ]; do
  case "$1" in
    --instance-type*)
      if [[ "$1" != *=* ]]; then shift; fi
      INSTANCE_TYPE="${1#*=}"
      ;;
    --availability-zone*)
      if [[ "$1" != *=* ]]; then shift; fi
      AVAILABILITY_ZONE="${1#*=}"
      ;;
    --volume-size*)
      if [[ "$1" != *=* ]]; then shift; fi
      VOLUME_SIZE="${1#*=}"
      ;;
    --image*|-i*)
      if [[ "$1" != *=* ]]; then shift; fi
      IMAGE="${1#*=}"
      ;;
    --tag*|-t*)
      if [[ "$1" != *=* ]]; then shift; fi
      TAG="${1#*=}"
      ;;
    --help|-h)
      printf "$USAGE" # Flag argument
      exit 0
      ;;
    *)
      >&2 printf "Error: Invalid argument\n"
      exit 1
      ;;
  esac
  shift
done

AVAILABILITY_ZONE=${AVAILABILITY_ZONE:-"eu-central-1a"}
INSTANCE_TYPE=${INSTANCE_TYPE:-"m5dn.2xlarge"}
VOLUME_SIZE=${VOLUME_SIZE:-150}
IMAGE=${IMAGE:-"mhub"}
TAG=${TAG:-"stable"}

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

if [ ! -f ".env" ]; then
    echo "no .env file found"
    exit 0
fi;

USER_DATA="$(./generate_user_data.sh --image $IMAGE --tag $TAG --volume-size $VOLUME_SIZE --base64)"

sed "s@USER_DATA@${USER_DATA}@g; \
    s/VOLUME_SIZE/${VOLUME_SIZE}/g; \
    s/AVAILABILITY_ZONE/${AVAILABILITY_ZONE}/g; \
    s/INSTANCE_TYPE/${INSTANCE_TYPE}/g;" skeletons/spot_config_skeleton.json
