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
    apache2 \
    curl \
    libapache2-mod-fastcgi \
    libapache2-mod-mapcache \
    mapcache-tools \
    python3-dateutil \
    python3-boto3 \
    sqlite3

EXPOSE 80
RUN mkdir /map && chmod 755 /map && mkdir /caches
CMD apachectl -D FOREGROUND