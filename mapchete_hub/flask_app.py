"""
Main web application.

This module configures Flask and defines all required endpoints.

API:

/capabilities.json
------------------
Show remote package versions, processes, etc.

/jobs
-----
Return submitted jobs. Jobs can be filtered by using the following keyword arguments:
    output_path : str
        Filter by output path.
    state : str
        Filter by job state.
    command : str
        Filter by mapchete Hub command.
    queue : str
        Filter by queue.
    job_name : str
        Filter by job name.
    bounds : list or tuple
        Filter by spatial bounds.
    from_date : str
        Filter by earliest date.
    to_date : str
        Filter by latest date.

/jobs/<job_id>
--------------
Return job metadata.

/processes
----------
Return available processes.

/processes/<process_id>
-----------------------
Return detailed information on process.

/queues
-------
List available queues, also showing number of pending jobs and workers attatched to each
queue.

/queues/<queue_name>
--------------------
Show detailed information on queue.
"""

from flask import Flask
from flask_pymongo import PyMongo
from flask_restful import Api
import logging
from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import (
    get_flask_config,
)
from mapchete_hub.log import update_logger
from mapchete_hub.resources import (
    Capabilities, Jobs, JobsOverview, Queues, QueuesOverview
)


logger = logging.getLogger(__name__)


def flask_app(log_level="INFO", full=True):
    """Initialize and return Flask app."""
    logger.debug("initialize flask app")
    app = Flask(__name__)

    # set app log level according to kwarg
    app.logger.setLevel(log_level)

    # configure app
    app.config.from_object(get_flask_config())

    # Flask app has to be called also for Celery workers. Here, we skip adding
    # all of the REST endpoints and MongoDB connection.
    if full:
        # add REST endpoints
        logger.debug("add REST endpoints")
        api = Api(app)
        api.add_resource(Capabilities, "/capabilities.json")
        api.add_resource(QueuesOverview, "/queues")
        api.add_resource(Queues, "/queues/<string:queue_name>")
        api.add_resource(JobsOverview, "/jobs", resource_class_kwargs=dict(app=app))
        api.add_resource(
            Jobs, "/jobs/<string:job_id>", resource_class_kwargs=dict(app=app)
        )

        # add logger to gunicorn logger
        if __name__ != "__main__":
            gunicorn_logger = logging.getLogger("gunicorn.error")

            # flas app logger
            app.logger.handlers = gunicorn_logger.handlers
            app.logger.setLevel(gunicorn_logger.level)

            # mapchete loggers
            update_logger(
                handlers=gunicorn_logger.handlers,
                loglevel=gunicorn_logger.level
            )

        # add MongoDB backend
        try:
            app.logger.debug("connect to MongoDB...")
            app.mongodb = PyMongo(app, tz_aware=True)
            app.logger.debug(app.mongodb.cx.server_info())  # pragma: no cover
        except:
            # don't raise if app is in testing mode - we mock the MongoDB in conftest.py
            # https://stackoverflow.com/questions/56029111/how-do-i-mock-pymongo-for-testing-with-a-flask-app
            if not app.testing:  # pragma: no cover
                app.logger.error(
                    "you must provide MHUB_BROKER_URI, MHUB_RESULT_BACKEND_URI and "
                    "MHUB_STATUS_DB_URI environment variables"
                )
                raise
            app.logger.debug("mocking PyMongo because app runs in testing mode")
        app.logger.debug("connected to MongoDB")

    # add Celery
    app.logger.debug("add Celery")
    celery_app.conf.update(app.config)
    celery_app.init_app(app)

    logger.debug("return Flask app")
    return app
