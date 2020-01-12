#########
Changelog
#########

---
0.6
---
* fix query error when filtering by queues or commands (#73)
* enable posting of custom process file (#52)
* fix rendering artefacts by changing mapserver scaling
* remove AWS credentials from mapfile & adapted starter script to temporarily include credentials from environment
* increased ``eox_preprocessing`` dependency to ``0.8``
* increased base image version for Dockerfile to ``0.3``
* added AWS management scripts
* use multistage docker builds to reduce image size

---
0.5
---
* enable filters to better query jobs (#53)
* print more details using ``mhub jobs`` and ``mhub status <job_id>``
* rename ``mapchete_hub.worker`` module to ``mapchete_hub.commands``
* remember timestamp on ``task-received`` and ``task-started`` events in ``started`` property
* add Celery-Slack integration (#26)
* add ``mhub batch`` command
* pass on mapchete config as ``OrderedDict`` (#48)
* serialize Cerlery messages as ``JSON`` instead of pickling
* fix ``announce_on_slack`` setting (#66 #25)

---
0.4
---
* fixed preprocessing dependency from version 0.4 to 0.5

---
0.3
---
* Docker image registry.gitlab.eox.at/maps/mapchete_hub/mhub:0.3
    * bases on registry.gitlab.eox.at/maps/docker-base/mapchete:0.2
* add ``mhub execute`` and ``mhub index`` commands (#54)
* API returns more useful error message for client
* automatically assign job ID (#64)
* only use one docker image for all mhub services: registry.gitlab.eox.at/maps/mapchete_hub/mhub

---
0.2
---
* Docker image registry.gitlab.eox.at/maps/mapchete_hub/mhub:0.2
    * bases on registry.gitlab.eox.at/maps/docker-base/mapchete:0.1
* celery worker now capture logs again (#62)
* zone_worker and preview_worker modules renamed to execute and index like their mapchete counterparts (#60)
* use tagged versions instead of branches in docker base images & depdendencies (#58)
* move mapserver and mapcache docker images to docker-base repository (#57)
* generate capabilities.json (#51)
* filter jobs by process output path (#40)
* list available processes
* list active queues and workers
* use built-in mapchete batch functions (#47)
* added better unit test coverage for most flask & celery related code parts (#7)
* start monitor in child process (#23)
* use built-in mapchete batch functions (#47)
* deploy application as WSGI using gunicorn (#20)
* added `mapchete_hub.api.API` class which abstracts all the relevant requests to the API
* when starting a worker, a queue can be specified which solves (#32)
* switched to `mapchete_satellite` backend
* added image filter functions
* pyproj metis support 1.9.5.1
* Sentinel-1 integration and images
* mhub, broker, etc. s1processor for mundi

---
0.1
---

* first build
