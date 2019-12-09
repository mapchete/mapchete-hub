#!/bin/bash

DATA_DIR="/mnt/data"
VOLUME="/dev/nvme0n1"

sudo mkfs -t ext4 ${VOLUME}
sudo mkdir -p ${DATA_DIR}
sudo mount ${VOLUME} ${DATA_DIR}
sudo chown -R ubuntu: ${DATA_DIR}
