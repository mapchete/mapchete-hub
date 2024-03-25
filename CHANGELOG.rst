#########
Changelog
#########

2024.3.2 - 2024-03-25
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.3.3``


2024.3.1 - 2024-03-19
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.3.1``


2024.3.0 - 2024-03-18
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.3.0``
    * use base image ``2024.2.1``


2024.2.12 - 2024-02-23
----------------------

* core
  * fix slack messaging
  * offload job creation to background task


2024.2.11 - 2024-02-22
----------------------

* core
  * fix `slack_sdk.WebClient` call


2024.2.10 - 2024-02-22
----------------------

* core
  * add lifespan resources for FastAPI app (status DB handler, job threadpool, optional local dask cluster)
  * use `concurrent.futures.ThreadPool` instead of FastAPI background tasks to run jobs


2024.2.9 - 2024-02-20
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.6``


2024.2.8 - 2024-02-16
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.5``


2024.2.7 - 2024-02-15
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.4``

2024.2.6 - 2024-02-15
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.3``


2024.2.5 - 2024-02-15
---------------------

* core
  * only close connections to dask `Gateway` while not in use

* packaging
    * bump ``mapchete`` to ``2024.2.0``
    * bump ``mapchete-eo`` to ``2024.2.2``
    * use base image ``2024.2.0``


2024.2.4 - 2024-02-13
---------------------

* core
  * close connections to dask `Gateway` and `GatewayCluster` while not in use


2024.2.3 - 2024-02-13
---------------------

* core
  * keep connection to `GatewayCluster` open


2024.2.2 - 2024-02-13
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.1``


2024.2.1 - 2024-02-13
---------------------

* core
  * close connections to dask `Gateway` and `GatewayCluster` while not in use


2024.2.0 - 2024-02-12
---------------------

* packaging
    * bump ``mapchete-eo`` to ``2024.2.0``


2024.1.8 - 2024-01-26
---------------------

* core
  * fix Slack messages


2024.1.7 - 2024-01-17
---------------------

* CI
    * run all jobs on `privileged`` runners with `docker`

* packaging
    * bump ``mapchete`` to ``2024.1.5``

2024.1.6 - 2024-01-16
---------------------

* core
  * slack messages: report in slack threads instead of single messages
  * fix worker settings when adapting cluster

* packaging
    * replace ``Slacker`` dependency with ``slack_sdk``


2024.1.5 - 2024-01-15
---------------------

* core
  * slack messages: also print exception representation, not just traceback

* packaging
    * bump ``mapchete`` to ``2024.1.3``


2024.1.4 - 2024-01-15
---------------------

* core
  * allow aborting jobs in `pending` mode
  * differentiate between `submitted` and `started` time stamps
  * add retry mechanism on requesting the dask cluster
  * track Exception in DB using `repr()` instead of `str()` to better keep track of exception type

* packaging
    * bump ``mapchete_eo`` to ``2024.1.4``


2024.1.3 - 2024-01-12
---------------------
* packaging
    * bump ``mapchete_eo`` to ``2024.1.3``


2024.1.2 - 2024-01-12
---------------------
* CI
    * use base image ``2024.1.2``

* packaging
    * use base image ``2024.1.2``
    * bump ``mapchete`` to ``2024.1.2``
    * bump ``mapchete_eo`` to ``2024.1.2``


2024.1.1 - 2024-01-10
---------------------
* CI
    * add pushing to aws registry to eox gitlab CI


2024.1.0 - 2024-01-04
----------------------
* CI
    * use base image ``2024.1.0``

* packaging
    * use base image ``2024.1.0``
    * bump ``mapchete`` to ``2024.1.0``
    * bump ``mapchete_eo`` to ``2024.1.0``


2023.12.2 - 2023-12-13
----------------------
* CI
    * use base image ``2023.12.2``

* core
    * adaptive `DaskSpecs` and `DaskSettings` now can also be passed to `mapchete` under `dask_specs` in the yaml config

* packaging
    * use base image ``2023.12.2``
    * bump ``mapchete`` to ``2023.12.2``
    * add ``eox_preprocessing`` version ``2023.12.0`` for backwards compability


2023.12.1 - 2023-12-11
----------------------
* CI
    * use podman layer caching

* core 
    * fix `db.mongodb` jobs parsing
    * pass on `DaskSpecs` and `DaskSettings` to `cluster.get_dask_executor`
    * rewrite and use `cluster.cluster_adapt`
    * minor fixes to Slack messages


2023.12.0 - 2023-12-11 (broken)
-------------------------------
* packaging
    * bump ``dask`` to ``2023.12.0``
    * bump ``distributed`` to ``2023.12.0``
    * bump ``mapchete`` to ``2023.12.1``
    * bump ``mapchete_eo`` to ``2023.12.0``
    * clean up unused dependencies in ``pyproject.toml``

* CI
    * use base image ``2023.12.1``
    * add ``isort`` to pre-commit

* core 
    * `settings`: use `pydantic_settings` to collect mhub configuration from environment and defaults
    * use job states from `mapchete.enums.Status`
    * use completely refactored `mapchete.commands.execute` function with now integrated retries & observer classes in newly created `job_wrapper` module
    * use observer classes (in `observers` module) to update status DB and send Slack messages
    * create `db` submodule for mongo DB and memory status handlers
    * define `models.JobEntry` model to ship around job metadata in from status handlers
    * extract some functionality from `app` to `job_wrapper` and `cluster` modules


2023.11.0 - 2023-11-28
----------------------
* packaging
    * use base image ``2023.11.0`` also for CI
    * bump ``dask-gateway`` to ``2023.9.0``
    * bump ``dask-gateway-server`` to ``2023.9.0``
    * bump ``dask-kubernetes`` to ``2023.10.0``    
    * bump ``dask`` to ``2023.11.0``
    * bump ``distributed`` to ``2023.11.0``
    * bump ``fastapi`` to ``0.104.1``
    * bump ``mapchete`` to ``2023.11.0``
    * bump ``mapchete_eo`` to ``2023.11.0``


2023.9.0 - 2023-06-18
---------------------
* packaging
    * use base image ``2023.8.0`` for tests as well
    * bump ``fastapi`` to ``0.103.1``
    * restrict ``pydantic`` to ``<2.0.0``
    * add ``httpx`` to dependencies


2023.8.1 - 2023-08-21
---------------------
* packaging
    * use base image ``2023.8.0``
    * bump ``mapchete`` to ``2023.8.1``

2023.8.0 - 2023-08-21
---------------------
* packaging
    * bump ``eox_preprocessing`` to ``2023.8.0``


2023.7.1 - 2023-07-19
---------------------
* packaging
    * use base image ``2023.7.1``
    * bump ``dask`` to ``2023.5.0``
    * bump ``distributed`` to ``2023.5.0``
    * bump ``dask-gateway`` to ``2023.1.1``     
    * bump ``dask-kubernetes`` to ``2023.3.2``
    * bump ``eox_preprocessing`` to ``2023.7.3``
    * bump ``fastapi`` to ``0.100.0``
    * bump ``mapchete`` to ``2023.7.1``


2023.7.0 - 2023-07-06
---------------------

* packaging
    * use base image ``2023.7.0``
    * bump ``mapchete`` to ``2023.7.0``


2023.6.5 - 2023-06-13
---------------------

* core
    * add `retry_flag` to only wait for newly started jobs, if retried by `CancelledError`, go ahead and start processing without delay


2023.6.4 - 2023-06-13
---------------------

* core
    * wait for jobs in states `MHUB_PROCESSING_STATES` for `10` seconds with up to `MHUB_MAX_PARALLEL_JOBS` (default: 2)
    * add wait parameter `MHUB_PREPROCESSING_WAIT` (default: 0) after preprocessing to offset possible lag for `mongoDB` and `DaskExecutor` connection

2023.6.3 - 2023-06-10
---------------------

* core
    * add `fiona.open` to read `--area` files (tested and works on `s3` stored files)
    * if `bounds` and `area` given use intersection as geometry

* packaging
    * use base image ``2023.5.0``
    * revert ``mapchete`` to ``2023.4.1``

2023.6.2 - 2023-06-07 (incompatible with `mapchete_satellite>=2023.5.5`)
------------------------------------------------------------------------

* core
    * add passing `area` param to mhub config to initialize job geometry
    * add test for `area` as `WKT` geometry and as `fgb` vector file

* packaging
    * bump ``dask`` to ``2023.5.0``
    * bump ``distributed`` to ``2023.5.0``


2023.6.1 - 2023-06-07 (incompatible with `mapchete_satellite>=2023.5.5`)
------------------------------------------------------------------------

* packaging
    * use base image ``2023.6.0``
    * bump ``mapchete`` to ``2023.6.1``

* CI/CD
    * deactivate integration tests


2023.6.0 - 2023-06-04
---------------------

* core
    * fix retry of `CancelledError` by reinitializing the whole job to skip existing output 

* packaging
    * bump ``dask`` is ``2023.4.0``
    * bump ``distributed`` is ``2023.4.0``
    * bump ``mapchete`` to ``2023.4.1``
    * bump ``mapchete_satellite`` to ``2023.5.5``


2023.1.0 - 2023-01-30
---------------------

* core
    * integrate URLs into text of Slack messages
    * enable retrying jobs when they raise a `CancelledError` configurable by environment variable `MHUB_CANCELLEDERROR_TRIES`
    * try to get dask scheduler logs after a failed job

* packaging
    * use base image ``2023.1.1``
    * bump ``mapchete_satellite`` to ``2023.1.9``
    * bump ``s2brdf`` to ``2023.1.0``

* CI/CD
    * remove ``mhub-s1`` image

2022.12.1 - 2022-12-19
----------------------

* packaging
    * bump ``dask`` is ``2022.12.1``
    * bump ``dask-kubernetes`` is ``2022.12.0``
    * bump ``distributed`` is ``2022.12.1``
    * bump ``eox_preprocessing`` to ``2022.12.0``
    * bump ``mapchete`` to ``2022.12.0``
    * bump ``mapchete_satellite`` to ``2022.12.2``
    * use base image ``2022.12.0``    
    

2022.12.0 - 2022-12-15
----------------------

* packaging
    * bump ``mapchete`` to ``2022.11.2``
    * bump ``mapchete_satellite`` to ``2022.12.1``
    * use base image ``2022.11.2``


2022.11.3 - 2022-11-28
----------------------

* packaging
    * bump ``mapchete`` to ``2022.11.1``
    * bump ``mapchete_satellite`` to ``2022.11.4``


2022.11.2 - 2022-11-22
----------------------

* packaging
    * use `hatch` instead of `setuptools`
    * build, test and upload python package to registry for every release


2022.11.1 - 2022-11-22
----------------------

* packaging
    * bump ``eox_preprocessing`` to ``2022.11.1``
    * bump ``mapchete`` to ``2022.11.0``
    * bump ``mapchete_satellite`` to ``2022.11.3``
    * use base image ``2022.11.0``


2022.11.0 - 2022-11-17
----------------------

* packaging
    * bump ``dask`` to ``2022.11.0``
    * bump ``dask-gateway`` to ``2022.11.0``
    * bump ``dask-gateway-server`` to ``2022.11.0``
    * bump ``dask-kubernetes`` to ``2022.10.1``
    * bump ``distributed`` to ``2022.11.0``
    * bump ``eox_preprocessing`` to ``2022.11.0``
    * bump ``fastapi`` to ``0.87.0``
    * bump ``mapchete_satellite`` to ``2022.11.2``
    * run `pip check` after image build


2022.10.5 - 2022-10-25
----------------------

* packaging
    * bump ``planet-signals-generation`` to ``2022.10.3``
    * add and freeze ``mapchete_xarray`` to ``2022.10.0``

* core
    * reinstall and use ``numcodecs`` from pypi as to fill any library or dependency gaps


2022.10.4 - 2022-10-20
----------------------

* packaging
    * bump ``mapchete-satellite`` to ``2022.10.1``


2022.10.3 - 2022-10-17
----------------------

* packaging
    * bump ``planet-signals-generation`` to ``2022.10.2``
    * bump ``dask`` and ``distributed`` to ``2022.10.0```

* core
    * add `environment` parser for `dask_gateway.options`
    * add test for `dask_spec` in `settings.py`
    * enable parsing of `AWS`, `DASK`, `GDAL`, `MHUB`, `MAPCHETE`, `MP` ENV variable for `dask-scheduler` and `dask-worker`
    * fix `docker-compose.yml` the `--nprocs` to `--nworkers` to fit newer ``dask`` and ``distributed`` versions


2022.10.2 - 2022-10-13
----------------------

* packaging
    * bump ``planet-signals-generation`` to ``2022.10.1``


2022.10.1 - 2022-10-07
----------------------

* packaging
    * bump ``mapchete_satellite`` to ``2022.10.0``


2022.10.0 - 2022-10-07
----------------------

* packaging
    * bump ``dask-kubernetes`` to ``2022.9.0``
    * bump ``planet-signals-generation`` to ``2022.10.0``

2022.9.0 - 2022-09-16
---------------------

* core
    * add an optional in-memory status DB if no MongoDB is present
    * dask `LocalCluster()` now uses processes & threads by default
    * add `mhub-server` CLI to quickly start an mhub instance
    * adaptive scaling is now deactivated by default unles `MHUB_DASK_ADAPTIVE_SCALING` is set to `TRUE`

* CI/CD
    * run only integration tests on integration test stage
    * start mhub by using new `mhub-server` CLI instead of `uvicorn``
    * use in-memory status DB in tests instead of `mongomock.MongoClient()`

* packaging
    * use base image ``2022.9.0``
    * don't tag ``latest`` images anymore
    * use `dask-gateway` pypi release instead of building from source
    * bump ``dask`` to ``2022.9.0``
    * bump ``dask-gateway`` to ``2022.6.1``
    * bump ``dask-gateway-server`` to ``2022.6.1``
    * bump ``dask-kubernetes`` to ``2022.7.0``
    * bump ``distributed`` to ``2022.9.0``
    * bump ``fastapi`` to ``0.85.0``
    * bump ``mapchete`` to ``2022.9.0``


2022.5.0 - 2022-05-05
---------------------

* CI/CD
  * every pushed commit now generates a docker image with the short commit hash as tag
  * split up into unit and integration tests
  * dump pip installed packages and versions as build job artefacts

* packaging
  * update dependencies: `dask==2022.5.0`, `dask-kubernetes==2022.4.1`, `distributed==2022.5.0`, `mapchete_satellite>=2022.5.0`
  * add `planet-signals-generation`


2022.4.0 - 2022-04-01
---------------------

* core
    * fix cluster size adaption

* packaging
    * use base image ``2022.4.0``


2022.3.2 - 2022-03-31
---------------------

* core
    * align <job_id>/results with current OAPI standard

* packaging
    * use base image ``2022.3.2``


2022.3.1 - 2022-03-29
---------------------

* packaging
    * bump ``dask-gateway`` to ``0a69d3d711a7bd472c724ad5d58c11d5a8ced61d``
    * bump ``dask`` to ``2022.3.0``


2022.3.0 - 2022-03-18
---------------------

* packaging
    * use base image ``2022.3.1``


2022.2.2 - 2022-02-25
---------------------

* core
    * request dask cluster after job was initialized
    * process dask task graph per default
    * use different adapt_options if dask task graph is used

* packaging
    * set ``mapchete`` to ``2022.2.2``
    * set ``mapchete_satellite`` to ``2022.2.0``


2022.2.0 - 2022-02-03
---------------------

* packaging
    * set ``mapchete`` to ``2022.2.0``
    * freeze ``dask-gateway`` to commit ``bee9255e5ea0d77f456985cd91b2622bb3776dbb``


2022.1.6 - 2022-01-31
---------------------

* packaging
    * set ``dask`` and `distributed` to ``2022.1.1``
    * set ``dask-kubernetes`` to ``2022.1.0``
    * set ``mapchete`` to ``2022.1.2``


2022.1.5 - 2022-01-26
---------------------

* packaging
    * set ``mapchete_satellite`` to ``2022.1.2``


2022.1.4 - 2022-01-19
---------------------

* packaging
    * set ``mapchete_satellite`` to ``2022.1.1``


---------------------
2022.1.3 - 2022-01-19
---------------------

* packaging
    * use base image ``2022.1.0``
    * set ``mapchete_satellite`` to ``2022.1.0``


---------------------
2022.1.2 - 2022-01-17
---------------------

* core
    * use context managers for all dask Client and Cluster instances
    * add more meaningful logger.info messages


---------------------
2022.1.1 - 2022-01-17
---------------------

* packaging
    * set ``eox_preprocessing`` to ``2021.1.0``
    * set ``fastAPI`` to ``0.72.0``


---------------------
2022.1.0 - 2022-01-13
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
