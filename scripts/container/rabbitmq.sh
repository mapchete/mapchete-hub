#!/bin/bash

# set environment variables
RABBITMQ_DEFAULT_USER="mhub"
RABBITMQ_DEFAULT_PASS="uwoo0aVo"

# install docker if not available
if ! [ -x "$(command -v docker)" ]; then
  echo "Error: docker is not installed." >&2
  # install and configure docker
  curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh
  sudo usermod -aG docker ubuntu
  sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
  sudo chmod g+rwx "/home/$USER/.docker" -R
  # make dirs
  sudo mkdir -p /mnt/data/log
  sudo chown -R ubuntu:ubuntu /mnt/data
  # install tools
  sudo apt install -y htop
fi

# set environment and run containers
docker run \
  --rm \
  --name=rabbitmq \
  -p 5672:5672 \
  -p 8080:8080 \
  -e RABBITMQ_DEFAULT_USER=$RABBITMQ_DEFAULT_USER \
  -e RABBITMQ_DEFAULT_PASS=$RABBITMQ_DEFAULT_PASS \
  -d \
  rabbitmq:3
