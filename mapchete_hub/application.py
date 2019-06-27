from flask import Flask, jsonify, request, abort, make_response
from flask_restful import Api, Resource
import json
import logging
from mapchete.config import get_zoom_levels
from mapchete.tile import BufferedTilePyramid
from multiprocessing import Process
import os
from shapely.geometry import box, mapping
from shapely import wkt

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import flask_options, main_options
from mapchete_hub._core import cleanup_config
from mapchete_hub.monitor import StatusHandler, status_monitor
from mapchete_hub._misc import cleanup_datetime
from mapchete_hub.workers import zone_worker, preview_worker


logger = logging.getLogger(__name__)
states = StatusHandler(
    os.path.join(main_options.get("config_dir"), main_options.get("status_gpkg")),
    mode="r",
    profile=main_options["status_gpkg_profile"]
)


workers = {
    'zone_worker': zone_worker,
    'preview_worker': preview_worker
}


def get_next_jobs(job_id=None, config=None, process_area=None):
    logger.debug("get next jobs: %s", config.keys())

    def _gen_next_job(next_c):
        logger.debug(next_c.keys())
        while True:
            if 'mhub_next_process' in next_c:
                job_conf = next_c['mhub_next_process']
                worker = job_conf['mhub_worker']
                kwargs = dict(
                    config=cleanup_config(dict(mapchete_config=next_c)),
                    process_area=process_area
                )
                task_id = '%s_%s' % (worker, job_id)
                kwargsrepr = json.dumps(kwargs)
                yield workers[worker].run.signature(
                    args=(None, ),
                    kwargs=kwargs,
                    task_id=task_id,
                    kwargsrepr=kwargsrepr
                )
                next_c = job_conf
            else:
                break

    mp_config = cleanup_datetime(config['mapchete_config'])
    return list(_gen_next_job(mp_config))


def flask_app(monitor=False):
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
    api.add_resource(JobsOverview, '/jobs/')
    api.add_resource(Jobs, '/jobs/<string:job_id>')

    if monitor:
        logger.debug("start monitor in child process")
        monitor = Process(target=status_monitor, args=(celery_app, ))
        monitor.start()

    logger.debug("return app")
    # Return the application instance.
    return app


class JobsOverview(Resource):

    def get(self):
        return jsonify(states.all())


class Jobs(Resource):

    def get(self, job_id):
        res = states.job(job_id)
        logger.debug("return get(): %s", res)
        if res:
            return make_response(jsonify(res), 200)
        else:
            abort(404)

    def post(self, job_id):
        config = request.get_json()
        mhub_worker = config['mapchete_config']['mhub_worker']
        mhub_queue = config['mapchete_config'].get(
            'mhub_queue', "%s_queue" % mhub_worker
        )

        res = states.job(job_id)

        # job exists
        if res:
            logger.debug("job already exists: %s", job_id)
            return make_response(jsonify(res), 409)

        # job is new
        else:
            # pass on to celery cluster
            logger.debug("job is new: %s", job_id)
            process_area = process_area_from_config(config)
            logger.debug("process area: %s", process_area)

            kwargs = dict(
                config=cleanup_config(cleanup_datetime(config)),
                process_area=process_area.wkt
            )
            logger.debug("send task %s to queue %s", job_id, mhub_queue)
            celery_app.send_task(
                "mapchete_hub.workers.%s.run" % mhub_worker,
                task_id=job_id,
                queue=mhub_queue,
                kwargs=kwargs,
                kwargsrepr=json.dumps(kwargs),
                link=get_next_jobs(
                    job_id=job_id,
                    config=config,
                    process_area=process_area.wkt
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
    bounds = config.get('bounds')
    if bounds:
        return box(*bounds)

    # wkt_geometry
    wkt_geometry = config.get('wkt_geometry')
    if wkt_geometry:
        return wkt.loads(wkt_geometry)

    def _tp():
        return BufferedTilePyramid(
            config["mapchete_config"]["pyramid"]["grid"],
            metatiling=config["mapchete_config"]["pyramid"].get("metatiling", 1),
            pixelbuffer=config["mapchete_config"]["pyramid"].get("pixelbuffer", 0)
        )

    # point
    point = config.get('point')
    if point:
        x, y = point
        zoom_levels = get_zoom_levels(
            process_zoom_levels=config["mapchete_config"]["zoom_levels"],
            init_zoom_levels=config["zoom"]
        )
        return _tp().tile_from_xy(x, y, max(zoom_levels)).bbox

    # tile
    tile = config.get('tile')
    if tile:
        return _tp().tile(*tile).bbox

    # mapchete_config
    process_bounds = config.get('mapchete_config', {}).get('process_bounds')
    if process_bounds:
        return box(*process_bounds)

    # raise error if no process areas is given
    raise AttributeError("no bounds, wkt_geometry, point, tile or process bounds given.")
