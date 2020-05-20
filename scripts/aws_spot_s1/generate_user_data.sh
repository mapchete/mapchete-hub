#!/bin/bash
USAGE="Usage: $(basename "$0") [-h] TYPE

This script combines contents of the .env file and skeletons/ec2_user_data_skeleton.sh.

Parameters:
    -h      Show this help text and exit.
    TYPE    Print either as string or base64 encoded. (default: string)
"

if [ "$1" == "-h" ]; then
    echo "$USAGE"
    exit 0
fi

TYPE=${1:-"string"}

if [ ! -f ".env" ]; then
    echo "no .env file found"
    exit 0
fi;

if [ "$TYPE" == "string" ]; then
    sed -e "/# insert .env contents here/{r .env" -e "d}" skeletons/ec2_user_data_skeleton.sh
elif [ "$TYPE" == "base64" ]; then
    echo $(sed -e "/# insert .env contents here/{r .env" -e "d}" skeletons/ec2_user_data_skeleton.sh | base64 -w 0 -)
else
    echo "unknown output type $TYPE"
    exit0
fi
