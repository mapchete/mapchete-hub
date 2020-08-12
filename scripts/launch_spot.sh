#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

Launch spot instances containing a running & configured mhub worker container.

Parameters:
    -h, --help              Show this help text and exit.
    --instance-type         Instance type. (default: m5dn.2xlarge)
    -n, --instances         Number of instances to be started. (default: 1)
    --availability-zone     Zone to launch instances into. (default: eu-central-1a)
    --volume-size           Size of additional volume in GB. (default: 150)
    -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
    -t, --tag               Tag used for mhub image. (default: stable)
"

while [ $# -gt 0 ]; do
  case "$1" in
    --instance-type*)
      if [[ "$1" != *=* ]]; then shift; fi
      INSTANCE_TYPE="${1#*=}"
      ;;
    --instances*|-n*)
      if [[ "$1" != *=* ]]; then shift; fi
      INSTANCES="${1#*=}"
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
INSTANCES=${INSTANCES:-1}
IMAGE=${IMAGE:-"mhub"}
TAG=${TAG:-"stable"}

echo "Submit spot request of $INSTANCES $INSTANCE_TYPE instance(s) in zone $AVAILABILITY_ZONE using $IMAGE:$TAG with an extra volume size of ${VOLUME_SIZE}G?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) ./generate_spot_config.sh \
                    --availability-zone ${AVAILABILITY_ZONE} \
                    --instance-type ${INSTANCE_TYPE} \
                    --image ${IMAGE} \
                    --tag ${TAG} \
                    --volume-size ${VOLUME_SIZE} > spot_config.json || exit 1;
                aws ec2 request-spot-instances \
                    --instance-count ${INSTANCES} \
                    --cli-input-json file://spot_config.json;
                rm spot_config.json || true;
                break;;
        No ) exit;;
    esac
done
