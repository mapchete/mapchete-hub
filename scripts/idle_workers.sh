#!/bin/bash
#!/bin/bash
USAGE="Usage: $(basename "$0") [-h]

Connect to given worker.

Parameters:
    -h, --help              Show this help text and exit.
    -i, --identity-file     Identity file to connect to worker. (default: ~/.ssh/eox_specops.pem)
    -c, --command           Run custom command.
    --idle-threshold        Threshold to determine idle worker, i.e. value 15 average load must be less than. (default: 5)
"

while [ $# -gt 0 ]; do
  case "$1" in
    --identity-file*|-i*)
      if [[ "$1" != *=* ]]; then shift; fi
      IDENTITY_FILE="${1#*=}"
      ;;
    --command*|-c*)
      if [[ "$1" != *=* ]]; then shift; fi
      COMMAND="${1#*=}"
      ;;
    --idle-threshold*)
      if [[ "$1" != *=* ]]; then shift; fi
      IDLE_THRESHOLD="${1#*=}"
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
IDLE_THRESHOLD=${IDLE_THRESHOLD:-"5"}

for WORKER in $(mhub workers); do
  if [[ $WORKER == execute_worker* ]]; then
    LOAD=$(./live_worker_info.sh -w $WORKER --identity-file=$IDENTITY_FILE --command "cat /proc/loadavg")
    LOADS=( $LOAD )
    # 15 minute average
    # (1 minute would be [0], 5 minutes would be [1])
    AVG_LOAD="${LOADS[2]}"
    if (( $(echo "$AVG_LOAD < $IDLE_THRESHOLD" |bc -l) )); then
        echo "$WORKER is dead ($LOAD)"
        if [ "$COMMAND" ]; then
          echo "run command $COMMAND..."
          ./live_worker_info.sh -w $WORKER --identity-file=$IDENTITY_FILE --command "$COMMAND";
        fi
    else
        echo "$WORKER is alive ($AVG_LOAD in past 15 minutes)"
    fi
  fi
done;


