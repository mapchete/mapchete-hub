FROM ubuntu:16.04
MAINTAINER Joachim Ungar

# add ubuntugis-unstable repository & install mapserver
RUN apt -y update \
  && apt -y upgrade \
  && apt install -y software-properties-common \
  && add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable \
  && apt -y update \
  && apt install -y cgi-mapserver \
  && echo 'deb http://archive.ubuntu.com/ubuntu trusty multiverse' >> /etc/apt/sources.list \
  && echo 'deb http://archive.ubuntu.com/ubuntu trusty-updates multiverse' >> /etc/apt/sources.list \
  && echo 'deb http://security.ubuntu.com/ubuntu trusty-security multiverse' >> /etc/apt/sources.list \
  && apt -y update \
  && apt install -y \
    libapache2-mod-fastcgi \
    apache2 \
  && a2enmod actions cgi alias

# get naturalearth data
RUN apt install -y wget unzip \
  && mkdir /mapdata \
  && cd /mapdata \
  && wget https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_land.zip \
  && wget https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_ocean.zip \
  && unzip ne_10m_land.zip \
  && unzip ne_10m_ocean.zip

EXPOSE 80
RUN mkdir /map && chmod 755 /map
CMD apachectl -D FOREGROUND
