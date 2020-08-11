#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

This script combines contents of the .env file and skeletons/ec2_user_data_skeleton.sh.

Parameters:
    -h              Show this help text and exit.
    --base64        Either as "string" or "base64" encoded. (default: string)
    --volume-size   Size of additional volume in GB. (default: 150)
    --image, -i     Image to be used. (either mhub or mhub-s1) (default: mhub)
    --tag, -t       Tag used for mhub image. (default: stable)
"

while [ $# -gt 0 ]; do
  case "$1" in
    --base64) # Flag argument
      if [[ "$1" != *=* ]]; then shift; fi # Value is next arg if no `=`
      TYPE="base64"
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

TYPE=${TYPE:-"string"}
VOLUME_SIZE=${VOLUME_SIZE:-150}
IMAGE=${IMAGE:-"mhub"}
TAG=${TAG:-"stable"}

if [ ! -f ".env" ]; then
    echo "no .env file found"
    exit 0
fi;


if [ "$TYPE" == "string" ]; then
    sed -e "s/# insert params here/IMAGE=$IMAGE\nTAG=$TAG\nVOLUME_SIZE=$VOLUME_SIZE/g;
            /# insert .env contents here/{r .env" -e "d}" \
            skeletons/ec2_user_data_skeleton.sh
elif [ "$TYPE" == "base64" ]; then
    echo $(sed -e "s/# insert params here/IMAGE=$IMAGE\nTAG=$TAG\nVOLUME_SIZE=$VOLUME_SIZE/g;
            /# insert .env contents here/{r .env" -e "d}" \
            skeletons/ec2_user_data_skeleton.sh | base64 -w 0 -)
else
    echo "unknown output type $TYPE"
    exit 0
fi
