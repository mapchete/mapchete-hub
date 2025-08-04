.. image:: logo/mapchete_hub_grey.svg

Distributed mapchete processing.

.. |PyPI version| image:: https://img.shields.io/pypi/v/mapchete-hub.svg
   :target: https://pypi.org/project/mapchete-hub/
   :alt: PyPI version
.. |Build Status| image:: https://github.com/mapchete/mapchete-hub/actions/workflows/python-package.yml/badge.svg
   :target: https://github.com/mapchete/mapchete-hub/actions
   :alt: Build Status
.. |PyPI license| image:: https://img.shields.io/pypi/l/mapchete.svg
   :target: https://github.com/mapchete/mapchete-hub/blob/main/LICENSE
   :alt: PyPI license
.. |Code Coverage| image:: https://codecov.io/gh/mapchete/mapchete-hub/graph/badge.svg?token=VD1YOF3QA2
   :target: https://codecov.io/gh/mapchete/mapchete-hub
   :alt: Code Coverage

|PyPI version| |Build Status| |PyPI license|


**mapchete Hub** provides a RESTful web interface to the **mapchete** geospatial data processing engine. Its API is inspired by the **OGC API - Processes** standard and allows you to execute, manage, and scale your processing jobs over HTTP.

The main use cases for the Hub are running processing jobs asynchronously and scaling them up in the background, potentially using Dask for distributed computing.


Key Features
============

* 🌐 **OGC API - Processes inspired**: A REST API for submitting jobs, monitoring their status, and retrieving results.
* ⚙️ **Advanced Job Monitoring**: Inspect detailed job states (``pending``, ``running``, ``failed``, ``success``) and view the overall progress percentage for currently running jobs.
* 🚀 **Scalable Execution**: Can be configured to use Dask for distributed, parallel execution of jobs.
* 💬 **Slack Notifications**: Optionally sends job status updates directly to a configured Slack channel.
* 🐳 **Container-Ready**: Designed to be deployed in containerized environments like Docker, making it easy to scale your processing capabilities.


How It Works
============

1.  **Serve**: Start the **mapchete Hub** server. It listens for incoming job requests.
2.  **Prepare Job**: A client application prepares a job configuration as a JSON object that follows the `MapcheteJob schema <https://github.com/mapchete/mapchete-hub/blob/main/mapchete_hub/models.py#L29>`_.
3.  **Submit**: The client ``POST``\s the JSON configuration to the ``/jobs`` endpoint. The Hub validates it and returns a unique ``job_id``.
4.  **Monitor**: The client uses the ``job_id`` to poll the ``/jobs/{job_id}`` endpoint to track the job's status and progress.
5.  **Retrieve**: Once the job is successful, the results can be accessed from the location defined in the job's output configuration.


Getting Started
===============

Installation
------------

Install **mapchete Hub** and its dependencies from PyPI:

.. code-block:: bash

   pip install mapchete-hub

Running the Server
------------------

To start the server, simply run the following command:

.. code-block:: bash

   mhub-server start

The API documentation will be available at ``http://127.0.0.1:8000/docs``.

Interacting with the Hub
------------------------

While you can use tools like `curl`, the easiest way to interact with the Hub is by using the `mapchete-hub-cli <https://github.com/mapchete/mapchete-hub-cli>`_ package.

First, install the client:
.. code-block:: bash

   pip install mapchete-hub-cli

Next, create a job configuration file, for example `my_job.json`:

.. code-block:: json

   {
     "process": "mapchete.processes.examples.hillshade",
     "zoom_levels": [
       10
     ],
     "pyramid": {
       "grid": "geodetic"
     },
     "input": {
       "dem": "https://storage.googleapis.com/mapchete-test-data/cleantopo2/dem.tif"
     },
     "output": {
       "path": "./hillshade_output",
       "format": "GTiff",
       "dtype": "uint8",
       "bands": 1
     }
   }

Now, use the CLI to submit the job and check its status:

.. code-block:: bash

   # Submit the job
   mhub-cli submit my_job.json

   # The command will return a job_id. Use it to check the status:
   mhub-cli status <your_job_id>


Contributing
============

**mapchete Hub** is an open-source project and we welcome contributions! Please see the `Contributing Guide <https://github.com/mapchete/mapchete/blob/main/CONTRIBUTING.md>`_ in the main ``mapchete`` repository for guidelines on how to get started.

Acknowledgements
================

The initial development of **mapchete Hub** was made possible with the resources and support of `EOX IT Services GmbH <https://eox.at/>`_.