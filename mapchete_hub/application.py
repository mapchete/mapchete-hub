"""
Main web application.

This module configures Flask and defines all required endpoints.
"""

from flask import Flask, jsonify, request, abort, make_response
from flask_restful import Api, Resource
import json
import logging
from multiprocessing import Process
import os
import pkg_resources
from shapely.geometry import mapping
import uuid
from webargs import fields
from webargs.flaskparser import use_kwargs

from mapchete_hub import __version__
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands import get_command_func, get_command_func_path
from mapchete_hub.config import (
    cleanup_datetime,
    flask_options,
    main_options,
    process_area_from_config
)
from mapchete_hub.monitor import StatusHandler, status_monitor


logger = logging.getLogger(__name__)
states = StatusHandler(
    os.path.join(main_options.get("config_dir"), main_options.get("status_gpkg")),
    mode="r",
    profile=main_options["status_gpkg_profile"]
)


def get_next_jobs(config=None, **kwargs):
    """Append next jobs to queue."""
    def _gen_next_job(job_conf, **kwargs):
        while True:
            if "mhub_next_process" in job_conf:
                next_conf = job_conf["mhub_next_process"]
                worker = next_conf["mhub_worker"]
                job_kwargs = dict(
                    mapchete_config=next_conf,
                    **dict(kwargs, mode=next_conf.get("mhub_mode"))
                )
                task_id = uuid.uuid4().hex
                job_kwargs_repr = json.dumps(job_kwargs)
                yield get_command_func(worker).signature(
                    args=(None, ),
                    kwargs=job_kwargs,
                    task_id=task_id,
                    kwargsrepr=job_kwargs_repr
                )
                job_conf = next_conf
            else:
                break

    mapchete_config = cleanup_datetime(config["mapchete_config"])
    return list(_gen_next_job(mapchete_config, **kwargs))


def flask_app(launch_monitor=False):
    """Flask application factory. Initializes and returns the Flask application."""
    logger.debug("initialize flask app")
    app = Flask(__name__)
    logger.debug("initialize flask with: %s", flask_options)
    app.config.update(flask_options)
    api = Api(app)

    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.DEBUG)

    logger.debug("initialize celery with: %s", app.config)
    celery_app.conf.update(app.config)
    celery_app.init_app(app)

    logger.debug("add endpoints to REST API")
    api.add_resource(Capabilities, "/capabilities.json")
    api.add_resource(QueuesOverview, "/queues/")
    api.add_resource(JobsOverview, "/jobs/")
    api.add_resource(Jobs, "/jobs/<string:job_id>")

    if launch_monitor:
        logger.debug("spawn monitor in child process")
        monitor = Process(target=status_monitor, args=(celery_app, ))
        monitor.start()

    # Return the application instance.
    logger.debug("return app")
    return app


class Capabilities(Resource):
    """Resouce for capabilities.json."""

    def __init__(self):
        """Initialize resource."""
        processes = list(pkg_resources.iter_entry_points("mapchete.processes"))
        self._capabilities = {}
        self._capabilities["version"] = __version__
        self._capabilities["processes"] = {}
        for v in processes:
            process_module = v.load()
            self._capabilities["processes"][process_module.__name__] = {
                "name": process_module.__name__,
                "docstring": process_module.execute.__doc__
            }

    def get(self):
        """Return /capabilities.json."""
        # append current information on queues and workers
        insp = celery_app.control.inspect().active_queues()
        queues_out = {}
        for worker, queues in (insp or {}).items():
            for queue in queues:
                if queue["name"] not in queues_out:
                    queues_out[queue["name"]] = []
                queues_out[queue["name"]].append(worker)
        self._capabilities["queues"] = queues_out

        return jsonify(self._capabilities)


class QueuesOverview(Resource):
    """Resource for /queues."""

    def get(self):
        """Return queues."""
        return jsonify(celery_app.control.inspect())


class JobsOverview(Resource):
    """Resource for /jobs."""

    args = {
        "output_path": fields.Str(required=False),
        "state": fields.Str(required=False),
        "command": fields.Str(required=False),
        "queue": fields.Str(required=False),
        "bounds": fields.DelimitedList(fields.Float(), required=False),
        "from_date": fields.DateTime(required=False),
        "to_date": fields.DateTime(required=False),
    }

    @use_kwargs(args)
    def get(self, **kwargs):
        """Return jobs."""
        return jsonify(states.all(**kwargs))


class Jobs(Resource):
    """Resource for /jobs/<job_id>."""

    def get(self, job_id):
        """Return job metadata."""
        res = states.job(job_id)
        logger.debug("return get(): %s", res)
        if res:
            return make_response(jsonify(res), 200)
        else:
            abort(404)

    def post(self, job_id):
        """Receive new job."""
        raw = request.get_json()
        data = raw if isinstance(raw, dict) else json.loads(raw)

        try:
            command_path = get_command_func_path(data["mapchete_config"]["mhub_worker"])
            mhub_queue = data["mapchete_config"].get(
                "mhub_queue",
                "%s_queue" % command_path.split(".")[-2]
            )
        except Exception as e:
            logger.error(e)
            return make_response(jsonify(dict(message=str(e))), 400)

        res = states.job(job_id)
        # job exists
        if res:
            logger.debug("job already exists: %s", job_id)
            return make_response(jsonify(res), 409)

        # job is new
        else:
            # pass on to celery cluster
            logger.debug("job is new: %s", job_id)
            try:
                process_area = process_area_from_config(data)
            except Exception as e:
                logger.error(e)
                return make_response(jsonify(dict(message=str(e))), 400)
            logger.debug("process area: %s", process_area)

            kwargs = dict(data, process_area=process_area.wkt)
            logger.debug("send task %s to queue %s", job_id, mhub_queue)
            celery_app.send_task(
                str(command_path),
                task_id=job_id,
                queue=mhub_queue,
                kwargs=kwargs,
                kwargsrepr=json.dumps(kwargs),
                link=get_next_jobs(
                    config=data,
                    process_area=process_area.wkt,
                )
            )
            res = states.job(job_id)
            return make_response(
                jsonify(
                    dict(
                        geometry=mapping(process_area),
                        properties=dict(state="PENDING")
                    )
                ), 202
            )
