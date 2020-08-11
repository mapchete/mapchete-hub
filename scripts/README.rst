================
Launcher scripts
================

Note that if you use these scripts you need a ``.env`` file providing secret information your mapchete Hub cluster requires to run properly. Here is a list of required variables:

.. code-block:: none

    AWS_ACCESS_KEY_ID=<some_value>
    AWS_SECRET_ACCESS_KEY=<some_value>
    GITLAB_REGISTRY_TOKEN=<some_value>
    MONGO_INITDB_ROOT_USERNAME=<some_value>
    MONGO_INITDB_ROOT_PASSWORD=<some_value>
    MONGO_IP=<some_value>
    MHUB_BROKER_URI=<some_value>
    MHUB_CONFIG_DIR=<some_value>
    MHUB_DOCKER_IMAGE_TAG=<some_value>
    MHUB_LOGLEVEL=<some_value>
    MHUB_RESULT_BACKEND_URI=<some_value>
    MHUB_SLACK_NOTIFY=<some_value>
    MHUB_SLACK_WEBHOOK_URL=<some_value>
    MHUB_STATUS_DB_URI=<some_value>

-----------------------------
Start from within an instance
-----------------------------

The scripts starting with ``start_`` can be run from within a machine (such as an EC2 instance).


``start_backend.sh``
--------------------

.. code-block:: none

    Usage: start_backend.sh [-h]

    Start two MongoDB instances. One as a broker, the other one as job storage database.

    NOTE:
    This script needs further environmental variables in order to start the docker container
    properly:

     - MONGO_INITDB_ROOT_USERNAME
     - MONGO_INITDB_ROOT_PASSWORD

    These variables are also attempted to be read from an .env file from this directory.

    Parameters:
        -h, --help              Show this help text and exit.


``start_mapcache_worker.sh``
-----------------------------

.. code-block:: none

    Usage: start_mapcache_worker.sh [-h]

    Run mapcache instance hosting the WMTS preview.

    NOTE:
    This script needs further environmental variables in order to start the docker container
    properly:

     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - GITLAB_REGISTRY_TOKEN

    These variables are also attempted to be read from an .env file from this directory.

    Parameters:
        -h, --help              Show this help text and exit.
        -t, --tag               Tag used for mhub image. (default: stable)


``start_preview_worker.sh``
---------------------------

.. code-block:: none

    Usage: start_preview_worker.sh [-h]

    Run mhub index worker and mapserver containers.

    NOTE:
    This script needs further environmental variables in order to start the docker container
    properly:

     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - BROKER_USER
     - BROKER_PW
     - BROKER_IP
     - GITLAB_REGISTRY_TOKEN
     - SLACK_WEBHOOK_URL

    These variables are also attempted to be read from an .env file from this directory.

    Parameters:
        -h, --help              Show this help text and exit.
        -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
        -t, --tag               Tag used for mhub image. (default: stable)
        --mapserver-tag         Tag used for mapserver image. (default: 0.11)


``start_server.sh``
-------------------

.. code-block:: none

    Usage: start_server.sh [-h]

    Run mhub server and monitor containers.

    NOTE:
    This script needs further environmental variables in order to start the docker container
    properly:

     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - MHUB_BROKER_URI
     - MHUB_RESULT_BACKEND_URI
     - MHUB_STATUS_DB_URI
     - GITLAB_REGISTRY_TOKEN
     - MHUB_SLACK_WEBHOOK_URL

    These variables are also attempted to be read from an .env file from this directory.

    Parameters:
        -h, --help              Show this help text and exit.
        -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
        -t, --tag               Tag used for mhub image. (default: stable)


``start_worker.sh``
-------------------

.. code-block:: none

    Usage: start_worker.sh [-h]

    Run mhub worker container.

    NOTE:
    This script needs further environmental variables in order to start the docker container
    properly:

     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - MHUB_BROKER_URI
     - MHUB_RESULT_BACKEND_URI
     - GITLAB_REGISTRY_TOKEN
     - MHUB_SLACK_WEBHOOK_URL

    These variables are also attempted to be read from an .env file from this directory.

    Parameters:
        -h, --help              Show this help text and exit.
        -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
        -t, --tag               Tag used for mhub image. (default: stable)



--------------------------------
Launch workers on spot instances
--------------------------------


``launch_spot.sh``
------------------

.. code-block:: none

    Usage: launch_spot.sh [-h]

    Launch spot instances containing a running & configured mhub worker container.

    Parameters:
        -h, --help              Show this help text and exit.
        --instance-type         Instance type. (default: m5dn.2xlarge)
        -n, --instances         Number of instances to be started. (default: 1)
        --availability-zone     Zone to launch instances into. (default: eu-central-1a)
        --volume-size           Size of additional volume in GB. (default: 150)
        -i, --image             Image to be used. (either mhub or mhub-s1) (default: mhub)
        -t, --tag               Tag used for mhub image. (default: stable)
