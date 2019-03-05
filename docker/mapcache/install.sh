#!/bin/bash
echo "Running install.sh"
apt update
echo "Adding UbuntuGIS repo"
DEBIAN_FRONTEND=noninteractive apt install -y software-properties-common
add-apt-repository -y ppa:ubuntugis/ppa
apt update
echo "Installing packages"
DEBIAN_FRONTEND=noninteractive apt install -y libapache2-mod-mapcache \
  mapcache-tools sqlite3 curl apache2 python3-dateutil python3-redis \
  python3-boto3
rm -rf /var/lib/apt/lists/*