"""
Main web application.

This module configures Flask and defines all required endpoints.
"""

import celery
from flask import Flask, jsonify, request, abort, make_response
from flask_restful import Api, Resource
import json
import logging
from multiprocessing import Process
import os
import pkg_resources
from shapely import wkt
import uuid
from webargs import fields
from webargs.flaskparser import use_kwargs

from mapchete_hub import __version__
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands import command_func
from mapchete_hub.config import (
    cleanup_datetime,
    custom_process_tempfile,
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
        """
        Return job metadata.

        Parameters
        ----------
        job_id : str
            Unique job ID.

        Returns
        -------
        response
        """
        res = states.job(job_id)
        logger.debug("return get(): %s", res)
        if res:
            return make_response(jsonify(res), 200)
        else:
            abort(404)

    def post(self, job_id):
        """
        Receive new job or batch job. A batch job is simply a list of jobs.

        The configuration has to be appended as JSON to the request. If the configuration
        is a list, it will be handled as a batch job, if it is a dictionary it will be
        handled as a single job.

        A job configuration has to contain the following items:
        - command : str
            One of the mapchete_hub.commands items (execute or index)
        - job_name : str
            Only required for batch jobs, otherwise it is optional. Has to be unique
            within batch job.
        - job : str
            In batch jobs this references to a mapchete configuration of a prior job and
            can be used as an alternative to mapchete_config.
        - mapchete_config : dict
            A valid mapchete configuration. In batch jobs either this or job has to be
            provided.
        - mode : str
            One of "continue" or "overwrite". (default: "continue")

        Furthermore a job configuration has to contain one of the spatial subset items. In
        a batch job, only the first job needs to have a spatial subset item as all of the
        subsequent jobs inherit this:
        - bounds : list
            Left, bottom, right, top coordinate of process area.
        - point : list
            X and y coordinate of point over process tile.
        - tile : list
            Zoom, row and column of process tile.
        - wkt_geometry : str
            WKT representaion of process area.

        In addition, optional items can be provided:
        - queue : str
            Queue the job will be added to. If no queue is provided, it will be appended
            to the commmands default queue (i.e. execute_queue or index_queue.)
        - zoom : list or int
            Minimum and maximum zoom level or single zoom level.

        Parameters
        ----------
        job_id : str
            Unique job ID.

        Returns
        -------
        response
            202: If job was accepted.
            400: If JSON does not contain required or does contain malformed data.
            409: If job under this ID already exists.
            500: If an internal server error occured.
        """
        try:
            jobs = list(
                _jobs_params(
                    request.get_json(),
                    init_job_id=job_id,
                    dst_crs=main_options["status_gpkg_profile"]["crs"]
                )
            )
        except Exception as e:
            logger.error(e)
            return make_response(jsonify(dict(message=str(e))), 400)

        try:
            res = states.job(job_id)
            # job exists
            if res:
                logger.debug("job already exists: %s", job_id)
                return make_response(jsonify(res), 409)

            # job is new
            else:
                # pass on to celery cluster
                logger.debug("job is new: %s", job_id)
                process_area = jobs[0]["kwargs"]["process_area"]

                logger.debug("process area: %s", process_area)
                logger.debug("task %s has %s follow-up jobs", job_id, len(jobs[1:]))
                logger.debug("send task %s to queue %s", job_id, jobs[0]["queue"])

                # chain jobs sequentially
                celery.chain(
                    command_func(j["command"]).signature(**j) for j in jobs
                ).apply_async()

                return make_response(
                    jsonify(
                        dict(
                            bounds=wkt.loads(process_area).bounds,
                            geometry=process_area,
                            id=job_id,
                            properties=dict(state="PENDING")
                        )
                    ), 202
                )
        except Exception as e:
            logger.error(e)
            return make_response(jsonify(dict(message=str(e))), 500)


def _jobs_params(raw, init_job_id, dst_crs):
    data = raw if isinstance(raw, (dict, list, tuple)) else json.loads(raw)
    if isinstance(data, dict):
        logger.debug("single job received")
        jobs = [data]
    elif isinstance(data, (list, tuple)):
        logger.debug("batch job received")
        jobs = data
    else:
        raise TypeError(
            """JSON must contain either a dictionary or a list of dictionaries"""
        )

    process_area, process_area_process_crs = process_area_from_config(
        **jobs[0], dst_crs=dst_crs
    )

    parent_job_id = None
    job_id = init_job_id
    child_job_ids = [uuid.uuid4().hex for _ in jobs]
    for i, config in enumerate(jobs):
        child_job_id = child_job_ids[i]
        job_name = config.get("job_name", "unnamed_job")

        # check mapchete configuration
        if "mapchete_config" not in config:
            raise KeyError("mapchete_config not provided")
        if not isinstance(config["mapchete_config"], dict):
            raise TypeError(
                "%s: mapchete_config must be a dictionary, not %s" % (
                    job_name, type(config["mapchete_config"])
                )
            )
        # verify process code
        # by calling this context manager, a syntax check and import will be conducted
        # TODO maby a bad idea to run this on the server
        with custom_process_tempfile(config["mapchete_config"]):
            pass

        # process mode
        mode = config.get("mode", "continue")
        if mode not in ["continue", "overwrite"]:
            raise ValueError(
                "%s: mode must be one of continue, overwrite, not %s" % (
                    job_name, config["mode"]
                )
            )

        # mapchete hub command
        if not config.get("command", None):
            raise KeyError("%s: no command given" % job_name)

        # mapchete hub queue
        queue = config.get("queue") or "%s_queue" % config["command"]

        kwargs = dict(
            config,
            mode=mode,
            job_name=job_name,
            command=config["command"],
            queue=queue,
            parent_job_id=parent_job_id,
            child_job_id=child_job_id,
            mapchete_config=cleanup_datetime(config["mapchete_config"]),
            process_area=process_area.wkt,
            process_area_process_crs=process_area_process_crs.wkt,
        )

        yield dict(
            task_id=job_id,
            command=config["command"],
            queue=queue,
            args=(None, ),
            kwargs=kwargs,
            kwargsrepr=json.dumps(kwargs)
        )
        parent_job_id, job_id = job_id, child_job_id
