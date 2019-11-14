FROM registry.gitlab.eox.at/maps/mapchete_hub/base_image:latest
MAINTAINER Joachim Ungar

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG LOGLEVEL
ARG MHUB_BROKER_URL
ARG MHUB_RESULT_BACKEND

ENTRYPOINT ./manage.py monitor --loglevel=$LOGLEVEL
