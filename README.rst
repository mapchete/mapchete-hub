============
mapchete Hub
============

Distributed mapchete processing.

-----
Usage
-----

SSH login:

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.194.7.82


Current instances:

* mhub server: ``18.194.7.82``
* broker: ``18.197.182.82``
* preview_worker & joker machine: ``18.184.146.112``
* zone_workers:
  * ``18.185.36.186``
  * ``18.184.217.37``
  * ``18.196.203.127``
  * ``18.184.51.203``
  * ``18.184.137.159``
  * ``35.158.235.58``
  * ``18.185.29.120``
  * ``18.195.252.1``
  * ``18.197.48.227``
  * ``18.197.24.39``
  * ``18.196.192.168``
  * ``54.93.251.96``
  * ``52.59.192.0``
  * ``54.93.230.150``
  * ``18.184.5.111``
  * ``18.185.84.249``


mhub
----

log into mhub server & start venv

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.194.7.82
    workon venv


inspect commands:

.. code-block:: shell

    # list all jobs
    mhub jobs
    # list successful
    mhub jobs | grep SUCCESS
    # list failed
    mhub jobs | grep FAILURE
    # list currently processing
    mhub jobs | grep PROGRESS
    # dump as GeoJSON
    mhub jobs --geojson > current_jobs.geojson

    # job specific commands
    ## use one of the job_ids listed by mhub jobs
    ## when job is finished successfully, it prints the elapsed time
    ## when job failed, it prints latest traceback
    ## when job is in progress, it shows a progress bar
    mhub status <job_id>

    # print job as GeoJSON
    ## use this to find out IP of worker processing the job
    mhub status --geojson <job_id>


manually fix tiles
------------------

NOTE: shut down ``preview_worker`` before updating index files!

log into ``preview worker`` & start venv

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.184.146.112
    workon mapchete
    export AWS_ACCESS_KEY_ID=REDACTED_API_KEY AWS_SECRET_ACCESS_KEY=REDACTED_API_KEY

create overviews and update index files for zone ``17-78``:

.. code-block:: shell

    zone="6 17 78"
    mapchete execute overviews.mapchete --verbose --logfile missing.log -m 8 -b `tmx bounds $zone` -z 8 12 -o && mapchete index overviews.mapchete --verbose --shp --for_gdal --out_dir /mnt/data/indexes/ -b `tmx bounds $zone` -z 8 13

    # or use the script from the preview_worker home directory
    ./update_overview_zone.sh 6 17 78


create overviews and update index files for bounds ``-8.4375 36.5625 -5.625 39.375``:

.. code-block:: shell

    bounds="-8.4375 36.5625 -5.625 39.375"
    mapchete execute overviews.mapchete --verbose --logfile missing.log -m 8 -b $bounds -z 8 12 -o && \
    mapchete index overviews.mapchete --verbose --shp --for_gdal --out_dir /mnt/data/indexes/ -b $bounds -z 8 13

    # or use the script from the preview_worker home directory
    ./update_overviews_bounds.sh -8.4375 36.5625 -5.625 39.375


fix single tile over point

.. code-block:: shell

    point="6.5504 59.9003"
    bounds=`tmx -m 4 bounds -- \`tmx -m 4 tile -- 13 $point\``
    mapchete execute mosaic_north_nocache.mapchete --verbose --logfile missing.log -m 8 -b $bounds -z 8 13 -o && \
    mapchete index overviews.mapchete --verbose --shp --for_gdal --out_dir /mnt/data/indexes/ -b $bounds -z 8 13

    # or use the script from the preview_worker home directory
    ./reprocess_point.sh 6.5504 59.9003


fix smaller area over bounds ``5.7689 59.4053 6.1759 59.5111``

.. code-block:: shell

    bounds="5.7689 59.4053 6.1759 59.5111"
    mapchete execute mosaic_north_nocache.mapchete --verbose --logfile missing.log -m 8 -b $bounds -z 8 13 -o && \
    mapchete index overviews.mapchete --verbose --shp --for_gdal --out_dir /mnt/data/indexes/ -b $bounds -z 8 13

    # or use the script from the preview_worker home directory
    ./reprocess_bounds.sh 5.7689 59.4053 6.1759 59.5111


broker
------

list queues & workers:

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.197.182.82
    sudo rabbitmqctl list_queues


purge queue ``zone_queue``:

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.197.182.82
    sudo rabbitmqctl purge_queue zone_queue

Celery will remove all tasks from queue unless they are currently processed by a worker.


generate index files
--------------------

NOTE: shut down ``preview_worker`` before updating index files!

log into preview worker & start venv

.. code-block:: shell

    ssh -A -i ~/.ssh/eox_specops.pem ubuntu@18.184.146.112
    workon mapchete
    export AWS_ACCESS_KEY_ID=REDACTED_API_KEY AWS_SECRET_ACCESS_KEY=REDACTED_API_KEY

for all zoom levels:

.. code-block:: shell

    bounds="-33.75 22.5 56.25 84.375"
    mapchete index mosaic_north.mapchete --out_dir /mnt/data/indexes/ --shp --for_gdal --bounds $bounds


zoom level 8:

.. code-block:: shell

    bounds="-33.75 22.5 56.25 84.375"
    mapchete index mosaic_north.mapchete --out_dir /mnt/data/indexes/ --shp --for_gdal --bounds $bounds --zoom 8


------------
Installation
------------

see docker/base_app/Dockerfile


----------
Deployment
----------

Use ``run.sh`` scripts as user data when launching instances.

* ``docker/server/run.sh`` starts monitor container & devserver container
* ``docker/preview_worker/run.sh`` starts preview_worker container & mapserver container
* ``docker/zone_worker/run.sh`` starts zone_worker container


update instances
----------------

.. code-block:: shell

    docker container stop zone_worker
    docker pull registry.gitlab.eox.at/maps/mapchete_hub/base_worker:latest
    LOGLEVEL='DEBUG'
    LOGFILE=/mnt/data/log/worker.log
    AWS_ACCESS_KEY_ID='REDACTED_API_KEY'
    AWS_SECRET_ACCESS_KEY='REDACTED_API_KEY'
    MHUB_BROKER_URL='amqp://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
    MHUB_RESULT_BACKEND='rpc://s2processor:REDACTED_API_KEY@18.197.182.82:5672//'
    MHUB_CONFIG_DIR='/mnt/processes'
    WORKER='zone_worker'
    docker run \
      --rm \
      --name $WORKER \
      -e WORKER=$WORKER \
      -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
      -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
      -e MHUB_BROKER_URL=$MHUB_BROKER_URL \
      -e MHUB_RESULT_BACKEND=$MHUB_RESULT_BACKEND \
      -e MHUB_CONFIG_DIR=$MHUB_CONFIG_DIR \
      -e CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
      -e HOST_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4` \
      -e LOGLEVEL=$LOGLEVEL \
      -e LOGFILE=$LOGFILE \
      -v /mnt/data:/mnt/data \
      -d \
      registry.gitlab.eox.at/maps/mapchete_hub/base_worker:latest


-------
License
-------

MIT License

Copyright (c) 2018 `EOX IT Services`_

.. _`EOX IT Services`: https://eox.at/
