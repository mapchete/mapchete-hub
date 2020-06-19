============
mapchete Hub
============

Distributed mapchete processing.

.. image:: https://gitlab.eox.at/maps/mapchete_hub/badges/master/pipeline.svg
    :target: https://gitlab.eox.at/maps/mapchete_hub/commits/master

.. image:: https://gitlab.eox.at/maps/mapchete_hub/badges/master/coverage.svg
    :target: https://gitlab.eox.at/maps/mapchete_hub/commits/master


Mapchete Hub executes mapchete processes asynchronously in the cloud. The process management interface is a REST api. To submit and observe jobs, there is a command line tool included in this package: ``mhub``.

-----
Usage
-----

A fully functional mapchete Hub instance needs the following services:

* mongodb
* mhub server
* mhub monitor
* one or more mhub worker (execute_worker and/or index_worker)

Please consult the ``docker-compose.yml`` file to gather details.

Use the shell scripts in ``scripts/container`` to install docker, download the image and run the required service. Per default, the ``latest`` tag is used. To start a specifically tagged image, pass it on to the script:

.. code-block:: shell

    ./worker.sh 0.3


A mapchete process can be used in mapchete Hub if its inputs and outputs are not locally stored as we cannot be sure on which worker (or host) the process will run.


mhub CLI
--------

The ``mhub`` tool is not an admin tool but a user tool. It allows for submitting jobs, quering job states and statuses, current queues and workers of the mapchete Hub cluster and available processes to run.


mhub batch
~~~~~~~~~~

Submit a chain of processes with different mode & zoom level setting. This requires a ``.mhub`` file. (See ``tests/testdata/batch_example.mhub``)

.. code-block:: none

  Usage: mhub batch [OPTIONS] BATCH_FILE

    Execute a batch of processes.

  Options:
    -b, --bounds FLOAT...    Left, bottom, right, top bounds in tile pyramid
                             CRS.
    -p, --point FLOAT...     Process tiles over single point location.
    -g, --wkt-geometry TEXT  Take boundaries from WKT geometry in tile pyramid
                             CRS.
    -t, --tile INTEGER...    Zoom, row, column of single tile.
    -o, --overwrite          Overwrite if tile(s) already exist(s).
    --slack                  Post message to slack if batch completed
                             successfully.
    -v, --verbose            Print info for each process tile.
    -d, --debug              Print debug log output.
    --help                   Show this message and exit.


mhub cancel
~~~~~~~~~~~

This command cancels a running job and its follow-up jobs if the job is part of a batch job.

.. code-block:: none

  Usage: mhub cancel [OPTIONS] JOB_ID

    Cancel job.

  Options:
    -d, --debug  Print debug log output.
    --help       Show this message and exit.


mhub execute
~~~~~~~~~~~~

This is the asynchronous equivalent of ``mapchete execute``.

.. code-block:: none

  Usage: mhub execute [OPTIONS] [MAPCHETE_FILES]...

    Execute a process.

  Options:
    -z, --zoom TEXT          Single zoom level or min and max separated by ','.
    -b, --bounds FLOAT...    Left, bottom, right, top bounds in tile pyramid
                             CRS.

    -p, --point FLOAT...     Process tiles over single point location.
    -g, --wkt-geometry TEXT  Take boundaries from WKT geometry in tile pyramid
                             CRS.

    -t, --tile INTEGER...    Zoom, row, column of single tile.
    -o, --overwrite          Overwrite if tile(s) already exist(s).
    -v, --verbose            Print info for each process tile.
    -d, --debug              Print debug log output.
    -q, --queue TEXT         Queue the job should be added to.
    --help                   Show this message and exit.

If the process is started with ``mhub execute``, ``mhub_worker`` is set automatically to ``execute_worker`` and ``mhub_queue`` can be specified explicitly otherwise the job will be sent to ``execute_queue``.

mhub index
~~~~~~~~~~

This is the asynchronous equivalent of ``mapchete index``.

.. code-block:: none

  Usage: mhub index [OPTIONS] [MAPCHETE_FILES]...

    Create index of output tiles.

  Options:
    -z, --zoom TEXT          Single zoom level or min and max separated by ','.
    -b, --bounds FLOAT...    Left, bottom, right, top bounds in tile pyramid
                             CRS.

    -p, --point FLOAT...     Process tiles over single point location.
    -g, --wkt-geometry TEXT  Take boundaries from WKT geometry in tile pyramid
                             CRS.

    -t, --tile INTEGER...    Zoom, row, column of single tile.
    -v, --verbose            Print info for each process tile.
    -q, --queue TEXT         Queue the job should be added to.
    -d, --debug              Print debug log output.
    --help                   Show this message and exit.

If an index job is started with ``mhub index``, ``mhub_worker`` is set automatically to ``index_worker`` and ``mhub_queue`` can be specified explicitly otherwise the job will be sent to ``index_queue``.


mhub jobs
~~~~~~~~~

This command lists all submitted jobs and their current job state: PENDING, PROGRESS, RECEIVED, STARTED, SUCCESS, FAILURE.

.. code-block:: none

    Usage: mhub jobs [OPTIONS]

    Show current jobs.

  Options:
    -g, --geojson                   Print as GeoJSON.
    -p, --output_path TEXT          Filter jobs by output_path.
    -s, --state [todo|doing|done|pending|progress|received|started|success|failure]
                                    Filter jobs by job state.
    -c, --command [execute|index]   Filter jobs by command.
    -q, --queue TEXT                Filter jobs by queue.
    -b, --bounds FLOAT...           Left, bottom, right, top bounds in tile
                                    pyramid CRS.

    --since TEXT                    Filter jobs by timestamp since given time.
    --until TEXT                    Filter jobs by timestamp until given time.
    -n, --job-name TEXT             Filter jobs job name.
    -v, --verbose                   Print job details. (Does not work with
                                    --geojson.)

    -d, --debug                     Print debug log output.
    --help                          Show this message and exit.

More details on a job status can be printed using ``mhub status``


mhub processes
~~~~~~~~~~~~~~

List all available processes which can be used in a mapchete file.

.. code-block:: none

  Usage: mhub processes [OPTIONS]

    Show available processes.

  Options:
    -n, --process_name TEXT  Print docstring of process.
    --docstrings             Print docstrings of all processes.
    -d, --debug              Print debug log output.
    --help                   Show this message and exit.


mhub progress
~~~~~~~~~~~~~

Show progressbar if job state is PROGRESS.

.. code-block:: none

  Usage: mhub progress [OPTIONS] JOB_ID

    Show job progress.

  Options:
    -d, --debug  Print debug log output.
    --help       Show this message and exit.


mhub queues
~~~~~~~~~~~

List all queues together with the registered workers.

.. code-block:: none

  Usage: mhub queues [OPTIONS]

    Show available queues.

  Options:
    -n, --queue_name TEXT  Print detailed information on queue.
    -d, --debug            Print debug log output.
    --help                 Show this message and exit.


mhub remote-versions
~~~~~~~~~~~~~~~~~~~~

Show package versions installed on cluster.

.. code-block:: none

  Usage: mhub remote-versions [OPTIONS]

    Print package versions installed on remote mapchete Hub.

  Options:
    -d, --debug  Print debug log output.
    --help       Show this message and exit.


mhub status
~~~~~~~~~~~

Print detailed information on a job.

.. code-block:: none

  Usage: mhub status [OPTIONS] JOB_ID

    Show job status.

  Options:
    -g, --geojson  Print as GeoJSON.
    --traceback    Print only traceback if available.
    -d, --debug    Print debug log output.
    --help         Show this message and exit.


Cluster configuration options
-----------------------------

MHUB_BACKEND_CRS
~~~~~~~~~~~~~~~~

CRS used to store job geometries (default: `EPSG:4326`).

MHUB_CONFIG_DIR
~~~~~~~~~~~~~~~

Base directory for mapchete on host. (default: `/mnt/data`)

MHUB_BROKER_URI
~~~~~~~~~~~~~~~

URI to MongoDB instance used as broker, e.g.: `mongodb://mhub:REDACTED_API_KEY@mongodb:27017`

MHUB_RESULT_BACKEND_URI
~~~~~~~~~~~~~~~~~~~~~~~

URI to MongoDB instance used as backend for Celery, e.g.: `mongodb://mhub:REDACTED_API_KEY@mongodb:27017`

MHUB_STATUS_DB_URI
~~~~~~~~~~~~~~~~~~

URI to MongoDB instance used as database to store job metadata, e.g.: `mongodb://mhub:REDACTED_API_KEY@mongodb:27017`


------------
Installation
------------

.. code-block:: shell

    sudo apt install -y libgdal-dev libspatialindex-dev
    pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
    pip install .[cli,mundi,s1,xarray]


------
Docker
------

Build and upload mhub image
---------------------------

All required mhub services use the mhub base image: ``registry.gitlab.eox.at/maps/mapchete_hub/mhub``


.. code-block:: shell

    # this will create an image named registry.gitlab.eox.at/maps/mapchete_hub/mhub:<name_of_current_git_branch>
    ./build.sh
    # to use a custom image tag, pass it on to the script:
    ./build.sh 0.3


License
-------

MIT License

Copyright (c) 2018 - 2020 `EOX IT Services`_

.. _`EOX IT Services`: https://eox.at/
