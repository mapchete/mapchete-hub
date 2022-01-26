#########
Changelog
#########

2021.1.5 - 2022-01-26
---------------------

* packaging

    * set ``mapchete_satellite`` to ``2022.1.2``


2021.1.4 - 2022-01-19
---------------------

* packaging

    * set ``mapchete_satellite`` to ``2022.1.1``


---------------------
2021.1.3 - 2022-01-19
---------------------

* packaging

    * use base image ``2022.1.0``
    * set ``mapchete_satellite`` to ``2022.1.0``


---------------------
2021.1.2 - 2022-01-17
---------------------

* core

    * use context managers for all dask Client and Cluster instances
    * add more meaningful logger.info messages


---------------------
2021.1.1 - 2022-01-17
---------------------

* packaging

    * set ``eox_preprocessing`` to ``2021.1.0``
    * set ``fastAPI`` to ``0.72.0``


---------------------
2021.1.0 - 2022-01-13
---------------------

* core

    * use async for all fastAPI request functions


-----------------------
2021.12.10 - 2021-12-16
-----------------------

* core

    * pass on cluster.adapt() kwargs via 'adapt_options' section in dask specs JSON

* packaging

    * use base image ``2021.12.3``
    * set ``mapchete`` to ``2021.12.3``


----------------------
2021.12.9 - 2021-12-15
----------------------

* packaging

    * use base image ``2021.12.2``
    * set ``mapchete`` to ``2021.12.2``


----------------------
2021.12.8 - 2021-12-14
----------------------

* packaging

    * use base image ``2021.12.1``
    * set ``mapchete`` to ``2021.12.1``


----------------------
2021.12.7 - 2021-12-14
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.4`` (fix prior release)


----------------------
2021.12.6 - 2021-12-14
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.4``


----------------------
2021.12.5 - 2021-12-13
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.3``

----------------------
2021.12.4 - 2021-12-13
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.2``

----------------------
2021.12.3 - 2021-12-07
----------------------

* core

    * use 8 worker 2 threads (on an 8 core machine) default specification for dask workers

* packaging

    * set ``eox_preprocessing`` to ``2021.12.0``

----------------------
2021.12.2 - 2021-12-02
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.1``


----------------------
2021.12.1 - 2021-12-02
----------------------

* core

    * improve slack messages

* packaging

    * use base image ``2021.12.0``
    * set ``mapchete`` to ``2021.12.0``


----------------------
2021.12.0 - 2021-12-01
----------------------

* packaging

    * set ``mapchete_satellite`` to ``2021.12.0``

----------------------
2021.11.6 - 2021-11-26
----------------------
* dockerfile

    * add step with `go` to build wheels of `dask-gateway` packages

* packaging

    * use `latest/main` `dask-gateway` version
   

----------------------
2021.11.5 - 2021-11-24
----------------------

* core

    * cache BackendDB connection

* packaging

    * use base image ``2021.11.3``
    * add ``orgonite>=2021.11.0`` to dependencies


----------------------
2021.11.4 - 2021-11-18
----------------------

* core

    * add slack notifications

* packaging

    * set dask and distributed versions to ``2021.11.1``
    * set dask-kubernetes to ``2021.10.0``


----------------------
2021.11.3 - 2021-11-18
----------------------

* core

    * set cluster worker minimum as either default or tiles tasks
    * submit tasks in chunks, not one by one (see https://github.com/ungarj/mapchete/pull/387)

* packaging

    * set minimum mapchete version to ``2021.11.2``
    * use base image ``2021.11.2``


----------------------
2021.11.2 - 2021-11-16
----------------------

* core

    * set cluster worker maximum as maximum of preprocessing and tiles tasks
    * large jobs now start earlier and use less ressources (https://github.com/ungarj/mapchete/pull/384)

* packaging

    * set minimum mapchete version to ``2021.11.1``
    * use base image ``2021.11.1``


----------------------
2021.11.1 - 2021-11-05
----------------------

* core

    * fix cluster initialization


----------------------
2021.11.0 - 2021-11-05
----------------------

* core

    * enable posting custom dask specs as JSON

* packaging

    * re-enable ``mapchete_xarray``
    * use base image ``2021.11.0``


----------------------
2021.10.5 - 2021-10-22
----------------------

* core
    * add updated timestamp also on new job

* dependencies
    * ``mapchete_satellite`` version to ``2021.10.3``


----------------------
2021.10.4 - 2021-10-20
----------------------

* dependencies
    * ``mapchete_satellite`` version to ``2021.10.2``


----------------------
2021.10.3 - 2021-10-19
----------------------

* dependencies
    * ``mapchete`` version to ``2021.10.3``


----------------------
2021.10.2 - 2021-10-15
----------------------

* dependencies
    * ``mapchete_satellite`` version to ``2021.10.1``


----------------------
2021.10.1 - 2021-10-14
----------------------

* core
    * set worker threads to 1 in default dask specs

* dependencies
    * ``mapchete_satellite`` version to ``2021.10.0``
    * ``mapchete`` version to ``2021.10.1``


----------------------
2021.10.0 - 2021-10-01
----------------------

* packaging
  * change version numbering scheme to ``YYYY.MM.x``

* Docker
    * update base image ``docker-base``
        * ``mapchete:2021.10.1`` for mhub
        * ``snap-mapchete-ost:2021.10.1`` for mhub-s1


-----------------
0.24 - 2021-10-01
-----------------
* fix GeoJSON creation if ``bounds`` field is not available.


-----------------
0.23 - 2021-10-01
-----------------
* fix default random job names
* fix dask specs write into metadata
* add ``bounds`` to GeoJSON
* Docker
    * update base image ``docker-base``
        * ``mapchete:0.24`` for mhub
        * ``snap-mapchete-ost:0.24`` for mhub-s1


-----------------
0.22 - 2021-09-29
-----------------
* dependencies
    * ``mapchete_satellite`` version to ``0.17``
    * ``dask`` version to ``2021.9.1``
    * ``distributed`` version to ``2021.9.1``


-----------------
0.21 - 2021-09-23
-----------------
* add ``dask_dashboard_link`` to job metadata
* enable configuration of dask scheduler & workers via env variables when using dask gateway
* use black & flake8 for code
* re-enable full integration tests


-----------------
0.20 - 2021-09-17
-----------------
NOTE: major code changes!
* replaced Celery with dask
* moved CLI functionality and api module into separate ``mapchete_hub_cli`` package
* replaced ``flask`` with ``FastAPI``
* deactivated xarray and Sentinel-1 support/tests(!) for now


-----------------
0.19 - 2021-03-04
-----------------
* fixed the mhub state query (#120)
* Docker
    * `pip-compile` is now used to resolve dependeny graph before installing requirements
    * dependencies
        * update ``mapchete`` to ``>=0.38``
        * update ``mapchete_satellite`` to ``0.15``
        * update ``eox_preprocessing`` to ``0.13``
    * update base image ``docker-base``
        * ``mapchete:0:17`` for mhub
        * ``snap-mapchete-ost:0:17`` for mhub-s1


-----------------
0.18 - 2020-12-03
-----------------
* Docker
    * dependencies
        * update `mapchete_satellite` to `0.14`
            * pass ``AWS_REQUEST_PAYER`` to fiona cloudmask reading to enable reading of L1C masks
            * read_cloudmasks functions now support `cloud_types` arg
                * default: ['opaque', 'cirrus']
                * this allows to choose which cloudmasks will be read in all read functions


-----------------
0.17 - 2020-11-26
-----------------
* Docker
    * update to 0.16 base image
        * version updates
            * mapchete `0.37`
    * dependencies
        * update `mapchete_satellite` to `0.13`
            * replace catching all rasterio errors using ``mapchete.errors.MapcheteIOError`` class (!96)
            * make retry decoration settings configurable via env (!96)
                * ``MP_SATELLITE_IO_RETRY_TRIES`` (default: 3)
                * ``MP_SATELLITE_RETRY_DELAY`` (default: 1)
                * ``MP_SATELLITE_IO_RETRY_BACKOFF`` (default: 1)
            * packaging:
                * increase mapchete minimum dependency to 0.37 (!96)


-----------------
0.16 - 2020-11-25
-----------------
* Docker
    * update to 0.14 base image
        * version updates
            * GDAL `3.2.0`
    * dependencies
        * update `mapchete_satellite` to `0.12`
            * S2AWS_COG:
                * switch off catalog concurency for S2 STAC search endpoint (#82)
                * retry `rasterio.errors.CRSError` and `rasterio.errors.CRSError` (#83, #84)
    * make Dockerfile more dev-friendly (!101)
    * remove requester pays ENV setting as it should be provided on deployment (!101)
* starter scripts
    * added `AWS_DEFAULT_REGION` to starter scripts (#124)


-----------------
0.15 - 2020-11-12
-----------------
* main package
    * pin Celery dependency to <5.0.0 because of breaking changes in API
    * API
        * remove default progress timeout
    * CLI
        * better make use of tqdm api
* Docker
    * update to 0.13 base image
        * version updates
            * Fiona 1.8.17
            * GDAL 3.1.3
            * GEOS 3.7.1 (downgraded from 3.8.1)
            * OpenSAR Toolkit 0.9.8
            * proj 7.1.1
            * pyproj 2.6.1
    * dependencies
        * updated `mapchete_satellite` to `0.11`
            * enable S2AWS_COG archive
            * enable BRDF correction
    * use new internal PyPi instance from EOX GitLab to install internal packages
* testing
    * use CI_JOB_ID instead of random hash for docker-compose project in order to clean up running containers & volumes properly after test run


-----------------
0.14 - 2020-09-08
-----------------
* main package
    * add worker event rate limit (!85, #67)
    * CLI
        * fix missing output_path in verbose mode (!81)
        * fix worker count (!83)
        * add `mhub workers` subcommand (!84)
* starter scripts (#106)
    * restructured directories
    * added
        * `idle_workers.sh`
        * `live_worker_info.sh`
* Docker
    * use base image 0.12 which updates
        * GDAL `2.4.4` (downgraded from `3.0.4`)
        * proj `5.2.0` (downgraded from `6.3.2`)
    * install latest boto3 version
* testing
    * use random ports and use unique name for docker-compose project (!88)



-----------------
0.13 - 2020-08-04
-----------------
* main package
    * fix job termination (#108)
* Docker
    * use base image 0.11 which updates
        * GDAL `3.0.4`
        * Fiona `1.8.13.post1`
        * mapchete `0.35`


-----------------
0.12 - 2020-07-20
-----------------
* main package
    * use a MongoDB instance as message broker (!69)
    * use a MongoDB instance as backend database for jobs (!69, !70)
    * cancel jobs (!69, #4)
    * monitor does not have to run on same machine than server anymore (!69)
    * mapchete_satellite: increase remote timeout to 30s (!74, #88)
* testing
    * run integration tests using docker-compose (!69, #44)
    * retry test stage (!72)
* Docker
    * use mapchete_satellite 0.10
    * use base image 0.10 which updates
        * GDAL `3.1.2`
        * Fiona `1.8.13`
        * GEOS `3.8.1`
        * mapchete `0.34`
        * proj `6.3.2`
        * rasterio `1.1.4`
        * spatialite `5.0.0-beta0`
        * SQLite `3310100`


-----------------
0.11 - 2020-06-02
-----------------
* Docker
    * use mapchete_satellite 0.9
    * use base image 0.9 which updates OpenSAR toolkit to 0.9.7


-----------------
0.10 - 2020-05-25
-----------------
* Docker
    * use orgonite 0.6 and don't extra install Cython
    * use base image 0.8 which fixes ost version mismatch for `mhub_s1` image (#91)


----------------
0.9 - 2020-05-20
----------------
* repository
    * removed deprecated Mapfiles
* Docker
    * use base image 0.7
    * automate docker builds
    * add full zarr support in builds
* API
    * require to encode custom process code as base64 string
    * fix passing on query parameters to `/jobs/` endpoint (#89)


----------------
0.8 - 2020-02-27
----------------
* CLI
    * add ``--timeout`` parameter
    * increase verbose output
    * add ``--debug`` flag to all subcommands
    * add ``remote-versions`` query
* monitor
    * make sure job events have a ``job_id`` before updating the database
    * add ``job_name`` filter
    * rename ``StatusHandler.all()`` to ``StatusHandler.jobs()``
* API
    * don't append queue information in capabilities.json
    * add queue length (i.e. number of jobs waiting) to response
    * add /queues/<queue_name> to API
* seeding
    * added mercator configurations
    * fixed compression setting in mapfiles


----------------
0.7 - 2020-02-07
----------------
* increased ``eox_preprocessing`` dependency to ``0.9``
* mhub handles jobs with other CRSes than EPSG:4326 (fixes #59)

----------------
0.6 - 2020-01-12
----------------
* fix query error when filtering by queues or commands (#73)
* enable posting of custom process file (#52)
* fix rendering artefacts by changing mapserver scaling
* remove AWS credentials from mapfile & adapted starter script to temporarily include credentials from environment
* increased ``eox_preprocessing`` dependency to ``0.8``
* increased base image version for Dockerfile to ``0.3``
* added AWS management scripts
* use multistage docker builds to reduce image size

----------------
0.5 - 2019-11-23
----------------
* enable filters to better query jobs (#53)
* print more details using ``mhub jobs`` and ``mhub status <job_id>``
* rename ``mapchete_hub.worker`` module to ``mapchete_hub.commands``
* remember timestamp on ``task-received`` and ``task-started`` events in ``started`` property
* add Celery-Slack integration (#26)
* add ``mhub batch`` command
* pass on mapchete config as ``OrderedDict`` (#48)
* serialize Cerlery messages as ``JSON`` instead of pickling
* fix ``announce_on_slack`` setting (#66 #25)

----------------
0.4 - 2019-11-15
----------------
* fixed preprocessing dependency from version 0.4 to 0.5

----------------
0.3 - 2019-11-15
----------------
* Docker image registry.gitlab.eox.at/maps/mapchete_hub/mhub:0.3
    * bases on registry.gitlab.eox.at/maps/docker-base/mapchete:0.2
* add ``mhub execute`` and ``mhub index`` commands (#54)
* API returns more useful error message for client
* automatically assign job ID (#64)
* only use one docker image for all mhub services: registry.gitlab.eox.at/maps/mapchete_hub/mhub

----------------
0.2 - 2019-11-07
----------------
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

----------------
0.1 - 2018-06-25
----------------

* first build
