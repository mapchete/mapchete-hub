#!/bin/bash

DATA_DIR="/mnt/data"
VOLUME="/dev/$(lsblk | grep 150G | head -n1 | sed -e 's/\s.*$//')"

sudo mkfs -t ext4 ${VOLUME}
sudo mkdir -p ${DATA_DIR}
sudo mount ${VOLUME} ${DATA_DIR}
sudo chown -R ubuntu: ${DATA_DIR}
