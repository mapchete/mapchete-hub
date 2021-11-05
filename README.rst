============
mapchete Hub
============

Distributed mapchete processing.

.. image:: https://gitlab.eox.at/maps/mapchete_hub/badges/master/pipeline.svg
    :target: https://gitlab.eox.at/maps/mapchete_hub/commits/master

.. image:: https://gitlab.eox.at/maps/mapchete_hub/badges/master/coverage.svg
    :target: https://gitlab.eox.at/maps/mapchete_hub/commits/master


Mapchete Hub executes mapchete processes asynchronously in the cloud. The process management interface is a REST api. To submit and observe jobs, there is a command line tool available as a separate package.

-----
Usage
-----

A fully functional mapchete Hub instance needs the following services:

* mhub server
* mongodb
* either a dask scheduler with one or more dask workers or a dask gateway providing a dask cluster upon request

Please consult the ``docker-compose.yml`` file to gather details.

A mapchete process can be used in mapchete Hub if its inputs and outputs are not locally stored as we cannot be sure on which worker (or host) the process will run.


Configuration options
---------------------

MHUB_ADD_MAPCHETE_LOGGER
~~~~~~~~~~~~~~~~~~~~~~~~

Add mapchete logger to log output.

MHUB_BACKEND_CRS
~~~~~~~~~~~~~~~~

CRS used to store job geometries (default: `EPSG:4326`).

MHUB_MONGODB_URL
~~~~~~~~~~~~~~~~

URL to MongoDB instance used as backend to store job metadata, e.g.: `mongodb://mhub:REDACTED_API_KEY@mongodb:27017`

MHUB_DASK_GATEWAY_URL
~~~~~~~~~~~~~~~~~~~~~

URL to dask gateway if available.

MHUB_DASK_ADAPTIVE_SCALING
~~~~~~~~~~~~~~~~~~~~~~~~

Activate adaptive cluster scaling. (default: True)

MHUB_DASK_SCHEDULER_URL
~~~~~~~~~~~~~~~~~~~~~~~

URL to dask scheduler if available.

MHUB_IMAGE_TAG
~~~~~~~~~~~~~~

Image tag to be used when spawning new workers using dask gateway. (default: current mhub version)

MHUB_SCHEDULER_CORES
~~~~~~~~~~~~~~~~~~~~

Number of CPU cores of new scheduler spawned by dask gateway. (default: 1)

MHUB_SCHEDULER_MEMORY
~~~~~~~~~~~~~~~~~~~~~

RAM of new scheduler spawned by dask gateway. (default: 2)

MHUB_WORKER_CORES
~~~~~~~~~~~~~~~~~

Number of CPU cores of new worker spawned by dask gateway. (default: 1)

MHUB_WORKER_MEMORY
~~~~~~~~~~~~~~~~~~

RAM of new scheduler spawned by dask gateway. (default: 2)

MHUB_WORKER_EVENT_RATE_LIMIT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Limit frequency in seconds to send job updates to metadatabase. This eases the DB traffic especially for jobs with short running tasks. (default: 0.2)

------
Docker
------

Build and upload mhub image
---------------------------

All required mhub services use the mhub base image: ``registry.gitlab.eox.at/maps/mapchete_hub/mhub``


.. code-block:: shell

    # this will create an image named registry.gitlab.eox.at/maps/mapchete_hub/mhub:<name_of_current_git_branch>
    ./docker-build.sh
    # to use a custom image tag, pass it on to the script:
    ./docker-build.sh 0.3


License
-------

MIT License

Copyright (c) 2018 - 2021 `EOX IT Services`_

.. _`EOX IT Services`: https://eox.at/
