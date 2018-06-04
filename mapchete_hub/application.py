from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import logging

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import get_flask_options, get_main_options
from mapchete_hub.monitor import StatusHandler
from mapchete_hub.workers import zone_worker


logger = logging.getLogger(__name__)
# status = StatusHandler(get_main_options().get("status_gpkg"), mode="r")


def flask_app(config=None, no_sql=False):
    """Flask application factory. Initializes and returns the Flask application."""
    logger.debug("initialize flask app")
    app = Flask(__name__)
    conf = get_flask_options()
    if config:
        conf.update(**config)
    app.config.update(conf)
    api = Api(app)

    celery_app.conf.update(app.config)
    celery_app.init_app(app)

    logger.debug("add resources")
    api.add_resource(JobsOverview, '/jobs/')
    api.add_resource(Jobs, '/jobs/<string:job_id>')

    logger.debug("return app")
    # Return the application instance.
    return app


class JobsOverview(Resource):

    def get(self):
        return jsonify(status.all())


class Jobs(Resource):

    def get(self, job_id):
        res = status.job(job_id)
        if not res:
            return jsonify(dict(job_id=job_id, status="UNKNOWN"))
        else:
            return jsonify(res)

    def post(self, job_id):
        res = status.job(job_id)
        if res:
            return jsonify(res)

        # job is new, so read config, add to caches and send to celery

        config = request.get_json()
        job = dict(job_id=job_id, status="QUEUED", config=config)

        # pass on to celery cluster

        zone_worker.run.apply_async(
            kwargs=dict(config=config),
            task_id=job_id
        )
        return job
