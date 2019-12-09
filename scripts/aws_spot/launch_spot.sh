#!/bin/bash
USAGE="Usage: $(basename "$0") [-h] INSTANCES

Launch spot instances containing mhub installation, mhub environment settings & start script.

Parameters:
    -h   Show this help text and exit.
    -t   Instance type. (default: m5dn.2xlarge)
    -i   Number of instances to be started. (default: 1)
    -z   Zone to launch instances into. (default: eu-central-1a)
    -b   Block spot duration in minutes. Must be a multiple of 60. (default: 120)
"

while getopts i:z:b:t: option
    do
        case "${option}"
        in
            t) INSTANCE_TYPE=${OPTARG};;
            i) INSTANCES=${OPTARG};;
            z) AVAILABILITY_ZONE=${OPTARG};;
            b) BLOCK_DURATION=${OPTARG};;
        esac
    done
AVAILABILITY_ZONE=${AVAILABILITY_ZONE:-"eu-central-1a"}
BLOCK_DURATION=${BLOCK_DURATION:-120}
INSTANCES=${INSTANCES:-1}
INSTANCE_TYPE=${INSTANCE_TYPE:-"m5dn.2xlarge"}


if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

echo "Submit spot request of $INSTANCES $INSTANCE_TYPE instances in zone $AVAILABILITY_ZONE with block duration of $BLOCK_DURATION minutes?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) ./generate_spot_config.sh \
                    -z ${AVAILABILITY_ZONE} \
                    -b ${BLOCK_DURATION} \
                    -t ${INSTANCE_TYPE} > spot_config.json || exit 1;
                aws ec2 request-spot-instances \
                    --instance-count ${INSTANCES} \
                    --cli-input-json file://spot_config.json;
                rm spot_config.json || true;
                break;;
        No ) exit;;
    esac
done
