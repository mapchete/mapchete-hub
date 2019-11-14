from flask import Flask, jsonify, request, abort, make_response
from flask_restful import Api, Resource
import json
import logging
from mapchete.config import get_zoom_levels
from mapchete.tile import BufferedTilePyramid
from multiprocessing import Process
import os
import pkg_resources
from shapely.geometry import box, mapping
from shapely import wkt
import uuid
from webargs import fields
from webargs.flaskparser import use_kwargs

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import flask_options, main_options
from mapchete_hub._core import cleanup_config
from mapchete_hub._misc import cleanup_datetime
from mapchete_hub.monitor import StatusHandler, status_monitor
from mapchete_hub.workers import execute, index


logger = logging.getLogger(__name__)
states = StatusHandler(
    os.path.join(main_options.get("config_dir"), main_options.get("status_gpkg")),
    mode="r",
    profile=main_options["status_gpkg_profile"]
)


available_workers = {
    "execute_worker": execute,
    "index_worker": index,
}
deprecated_workers = {
    "zone_worker": execute,
    "preview_worker": index,
}


def get_next_jobs(config=None, **kwargs):
    """Append next jobs to queue."""
    def _gen_next_job(job_conf, **kwargs):
        while True:
            if "mhub_next_process" in job_conf:
                next_conf = job_conf["mhub_next_process"]
                worker = next_conf["mhub_worker"]
                job_kwargs = dict(
                    mapchete_config=cleanup_config(next_conf),
                    **dict(kwargs, mode=next_conf.get("mhub_mode"))
                )
                task_id = uuid.uuid4().hex
                job_kwargs_repr = json.dumps(job_kwargs)
                yield dict(available_workers, **deprecated_workers)[worker].run.signature(
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

    def __init__(self):
        processes = list(pkg_resources.iter_entry_points("mapchete.processes"))
        self._capabilities = {}
        self._capabilities["processes"] = {}
        for v in processes:
            process_module = v.load()
            self._capabilities["processes"][process_module.__name__] = {
                "name": process_module.__name__,
                "docstring": process_module.execute.__doc__
            }

    def get(self):
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

    def get(self):
        return jsonify(celery_app.control.inspect())


class JobsOverview(Resource):

    args = {"output_path": fields.Str(required=False)}

    @use_kwargs(args)
    def get(self, output_path=None):
        logger.debug("output_path: %s", output_path)
        return jsonify(states.all(output_path=output_path))


class Jobs(Resource):

    def get(self, job_id):
        res = states.job(job_id)
        logger.debug("return get(): %s", res)
        if res:
            return make_response(jsonify(res), 200)
        else:
            abort(404)

    def post(self, job_id):
        raw = request.get_json()
        data = raw if isinstance(raw, dict) else json.loads(raw)

        try:
            mhub_worker = dict(
                available_workers, **deprecated_workers
            )[data["mapchete_config"]["mhub_worker"]].__name__
            mhub_queue = data["mapchete_config"].get(
                "mhub_queue",
                "%s_queue" % mhub_worker.split(".")[-1]
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
                "%s.run" % mhub_worker,
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


def process_area_from_config(config):
    # bounds
    bounds = config.get("bounds")
    if bounds:
        return box(*bounds)

    # wkt_geometry
    wkt_geometry = config.get("wkt_geometry")
    if wkt_geometry:
        return wkt.loads(wkt_geometry)

    def _tp():
        return BufferedTilePyramid(
            config["mapchete_config"]["pyramid"]["grid"],
            metatiling=config["mapchete_config"]["pyramid"].get("metatiling", 1),
            pixelbuffer=config["mapchete_config"]["pyramid"].get("pixelbuffer", 0)
        )

    # point
    point = config.get("point")
    if point:
        x, y = point
        zoom_levels = get_zoom_levels(
            process_zoom_levels=config["mapchete_config"]["zoom_levels"],
            init_zoom_levels=config["zoom"]
        )
        return _tp().tile_from_xy(x, y, max(zoom_levels)).bbox

    # tile
    tile = config.get("tile")
    if tile:
        return _tp().tile(*tile).bbox

    # mapchete_config
    process_bounds = config.get("mapchete_config", {}).get("process_bounds")
    if process_bounds:
        return box(*process_bounds)

    # raise error if no process areas is given
    raise AttributeError("no bounds, wkt_geometry, point, tile or process bounds given.")
