#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

Connect to given worker.

Parameters:
    -h, --help              Show this help text and exit.
    -i, --identity-file     Identity file to connect to worker. (default: ~/.ssh/eox_specops.pem)
    -w, --worker            Worker name. (e.g. execute_worker@<IP>)
    -j, --job-id            ID of job which is currently executed on worker. (Cannot be used with --worker.)
    -c, --command           Run custom command.
    --htop                  Show htop output.
    --log                   Follow execute_worker log.
"

while [ $# -gt 0 ]; do
  case "$1" in
    --identity-file*|-i*)
      if [[ "$1" != *=* ]]; then shift; fi
      IDENTITY_FILE="${1#*=}"
      ;;
    --worker*|-w*)
      if [[ "$1" != *=* ]]; then shift; fi
      WORKER="${1#*=}"
      ;;
    --job-id*|-j*)
      if [[ "$1" != *=* ]]; then shift; fi
      JOB_ID="${1#*=}"
      ;;
    --command*|-c*)
      if [[ "$1" != *=* ]]; then shift; fi
      COMMAND="${1#*=}"
      ;;
    --htop) # Flag argument
      if [[ "$1" != *=* ]]; then shift; fi # Value is next arg if no `=`
      COMMAND="htop"
      ;;
    --log) # Flag argument
      if [[ "$1" != *=* ]]; then shift; fi # Value is next arg if no `=`
      COMMAND="docker logs -f --tail 100 execute_worker"
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

IDENTITY_FILE=${IDENTITY_FILE:-"~/.ssh/eox_specops.pem"}

if [ $WORKER ] && [ $JOB_ID ]; then
  echo "--worker and --job-id cannot be used at the same time"
  exit 1;
elif [ ! $WORKER ] && [ ! $JOB_ID ]; then
  echo "either --worker or --job-id have to be provided"
  exit 1;
elif [ $JOB_ID ]; then
  WORKER=`mhub status $JOB_ID | grep worker`
fi

WORKER_IP=${WORKER#*@}

ssh \
    -o StrictHostKeyChecking=no \
    -q \
    -i $IDENTITY_FILE \
    ubuntu@${WORKER_IP} \
    -t "$COMMAND"
