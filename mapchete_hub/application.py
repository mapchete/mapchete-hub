from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import logging

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import get_flask_options, get_main_options
from mapchete_hub.exceptions import UnknownJobState
from mapchete_hub.workers import zone_worker


logger = logging.getLogger(__name__)

# local jobs cache
registered_jobs = {}
success_jobs = {}
failed_jobs = {}
progress_jobs = {}
unknown_jobs = {}


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

    state_store = get_main_options().get("state_store_file")

    def get(self):
        update_jobs_caches()
        return jsonify(
            dict(
                unknown=list(unknown_jobs.keys()),
                success=list(success_jobs.keys()),
                failed=list(failed_jobs.keys()),
                progress=list(progress_jobs.keys()),
            )
        )


class Jobs(Resource):

    state_store = get_main_options().get("state_store_file")

    def get(self, job_id):
        if job_id not in registered_jobs:
            return jsonify(dict(job_id=job_id, status="UNKNOWN"))

        update_jobs_caches(job_id)
        return return_if_known(job_id)

    def post(self, job_id):
        update_jobs_caches(job_id)
        if job_id in registered_jobs:
            return return_if_known(job_id)

        # job is new, so read config, add to caches and send to celery
        config = request.get_json()
        job = dict(job_id=job_id, status="QUEUED", config=config)
        registered_jobs[job_id] = jsonify(job)
        unknown_jobs[job_id] = jsonify(job)
        # pass on to celery cluster
        zone_worker.run.apply_async(
            kwargs=dict(config=config),
            task_id=job_id
        )
        return job


def update_jobs_caches(job_id=None):
    if job_id is None:
        job_ids = registered_jobs
    else:
        job_ids = [job_id]

    for job_id in job_ids:

        if job_id not in registered_jobs:
            continue

        # if job previously was in a final state, skip
        if job_id in success_jobs or job_id in failed_jobs:
            print("%s already done" % job_id)
            continue

        res = celery_app.AsyncResult(job_id)
        res_meta = res.backend.get_task_meta(job_id)

        if res.status == "SUCCESS":
            _silent_del_key(job_id, unknown_jobs)
            _silent_del_key(job_id, progress_jobs)
            success_jobs[job_id] = jsonify(dict(res_meta, job_id=job_id))

        elif res.status == "FAILURE":
            _silent_del_key(job_id, unknown_jobs)
            _silent_del_key(job_id, progress_jobs)
            # celery writes Exception into result which cannot be parsed in JSON
            res_meta.update(result=None)
            failed_jobs[job_id] = jsonify(dict(res_meta, job_id=job_id))

        elif res.status == "PROGRESS":
            _silent_del_key(job_id, unknown_jobs)
            progress_jobs[job_id] = jsonify(dict(res_meta, job_id=job_id))

        elif res.status == "PENDING":
            _silent_del_key(job_id, progress_jobs)
            unknown_jobs[job_id] = jsonify(dict(res_meta, job_id=job_id))

        else:
            raise AttributeError("unknown state: %s", res.status)


def return_if_known(job_id):

    if job_id in success_jobs:
        return success_jobs[job_id]

    elif job_id in failed_jobs:
        return failed_jobs[job_id]

    elif job_id in unknown_jobs:
        return unknown_jobs[job_id]

    elif job_id in progress_jobs:
        return progress_jobs[job_id]

    else:
        raise UnknownJobState(job_id)


def _silent_del_key(k, d):
    try:
        del d[k]
    except KeyError:
        pass
