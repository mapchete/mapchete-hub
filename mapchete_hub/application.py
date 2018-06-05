from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import json
import logging
from mapchete.config import get_zoom_levels
from mapchete.tile import BufferedTilePyramid
from shapely.geometry import box, mapping
from shapely import wkt

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import get_flask_options, get_main_options
from mapchete_hub.monitor import StatusHandler
from mapchete_hub.workers import zone_worker


logger = logging.getLogger(__name__)
status = StatusHandler(
    get_main_options().get("status_gpkg"),
    mode="r",
    profile=get_main_options()["status_gpkg_profile"]
)


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
        # pass on to celery cluster
        kwargs = dict(config=config, process_area=process_area_from_config(config))
        zone_worker.run.apply_async(
            kwargs=kwargs, task_id=job_id, kwargsrepr=json.dumps(kwargs)
        )
        return status.job(job_id)


def process_area_from_config(config):
    # bounds
    bounds = config['bounds']
    if bounds:
        return box(*bounds).wkt

    # wkt_geometry
    wkt_geometry = config['wkt_geometry']
    if wkt_geometry:
        return wkt.loads(wkt_geometry).wkt

    def _tp():
        return BufferedTilePyramid(
            config["mapchete_config"]["pyramid"]["grid"],
            metatiling=config["mapchete_config"]["pyramid"].get("metatiling", 1),
            pixelbuffer=config["mapchete_config"]["pyramid"].get("pixelbuffer", 0)
        )

    # point
    point = config['point']
    if point:
        x, y = point
        zoom_levels = get_zoom_levels(
            process_zoom_levels=config["mapchete_config"]["zoom_levels"],
            init_zoom_levels=config["zoom"]
        )
        return _tp().tile_from_xy(x, y, max(zoom_levels)).bbox.wkt

    # tile
    tile = config['tile']
    if tile:
        return _tp().tile(*tile).bbox.wkt

    # mapchete_config
    process_bounds = config['mapchete_config'].get('process_bounds')
    if process_bounds:
        return box(*process_bounds).wkt

    # raise error if no process areas is given
    raise AttributeError("no bounds, wkt_geometry, point, tile or process bounds given.")
