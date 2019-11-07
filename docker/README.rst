=============
Docker images
=============

----------------
Available Images
----------------

For more details on versions and tags, see VERSIONS.rst


`base_image`
------------

Bases on `registry.gitlab.eox.at/maps/docker-base/mapchete` plus orgonite, mapchete_hub and eox_preprocessing.

```shell
docker pull registry.gitlab.eox.at/maps/mapchete_hub/base_image
```


`base_image_s1`
---------------

Bases on `registry.gitlab.eox.at/maps/docker-base/snap-mapchete` plus orgonite, metis, mapchete_hub and eox_preprocessing.

```shell
docker pull registry.gitlab.eox.at/maps/mapchete_hub/base_image_s1
```


`worker`
--------

Bases on `registry.gitlab.eox.at/maps/mapchete_hub/base_image` and starts mhub worker.

```shell
docker pull registry.gitlab.eox.at/maps/mapchete_hub/worker
```


`server`
--------

Bases on `registry.gitlab.eox.at/maps/mapchete_hub/base_image` and starts mhub server.

```shell
docker pull registry.gitlab.eox.at/maps/mapchete_hub/server
```


`monitor`
---------

Bases on `registry.gitlab.eox.at/maps/mapchete_hub/base_image` and starts mhub monitor.

```shell
docker pull registry.gitlab.eox.at/maps/mapchete_hub/monitor
```


-----------------------
Build and Upload Images
-----------------------

### build and upload all

(if no tag provided, `latest` is used)

```shell
./build.sh :all:
```

### build, upload and tag all

```shell
./build.sh :all: 0.1
```

### build and upload specific image
```shell
./build.sh mhub_base_image 0.1
```
