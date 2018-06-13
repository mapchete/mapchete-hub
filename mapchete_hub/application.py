from flask import Flask, jsonify, request, abort, make_response
from flask_restful import Api, Resource
import logging
from mapchete.config import get_zoom_levels
from mapchete.tile import BufferedTilePyramid
from shapely.geometry import box, mapping
from shapely import wkt

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import flask_options, main_options
from mapchete_hub.monitor import StatusHandler
from mapchete_hub import send_to_queue


logger = logging.getLogger(__name__)
states = StatusHandler(
    main_options.get("status_gpkg"),
    mode="r",
    profile=main_options["status_gpkg_profile"]
)


def flask_app(config=None, no_sql=False):
    """Flask application factory. Initializes and returns the Flask application."""
    logger.debug("initialize flask app")
    app = Flask(__name__)
    logger.debug("initialize flask with: %s", flask_options)
    app.config.update(flask_options)
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
        return jsonify(states.all())


class Jobs(Resource):

    def get(self, job_id):
        res = states.job(job_id)
        logger.debug("return get(): %s", res)
        if not res:
            logger.debug("send 404")
            abort(404)
        response = make_response(jsonify(res), 200)
        return response

    def post(self, job_id):
        config = request.get_json()
        mhub_worker = config['mapchete_config']['mhub_worker']

        res = states.job(job_id)
        if res:
            logger.debug("job already exists: %s", job_id)
            response = make_response(
                jsonify(
                    dict(
                        geometry=res["geometry"],
                        properties=dict(state="EXISTS")
                    )
                ), 409
            )
            return response

        # job is new
        # pass on to celery cluster
        process_area = process_area_from_config(config)
        logger.debug("process area: %s", process_area)
        send_to_queue(
            job_id=job_id,
            worker=mhub_worker,
            config=config,
            process_area=process_area
        )
        response = make_response(
            jsonify(
                dict(
                    geometry=mapping(process_area),
                    properties=dict(state="PENDING")
                )
            ), 202
        )
        return response


def process_area_from_config(config):
    # bounds
    bounds = config['bounds']
    if bounds:
        return box(*bounds)

    # wkt_geometry
    wkt_geometry = config['wkt_geometry']
    if wkt_geometry:
        return wkt.loads(wkt_geometry)

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
        return _tp().tile_from_xy(x, y, max(zoom_levels)).bbox

    # tile
    tile = config['tile']
    if tile:
        return _tp().tile(*tile).bbox

    # mapchete_config
    process_bounds = config['mapchete_config'].get('process_bounds')
    if process_bounds:
        return box(*process_bounds)

    # raise error if no process areas is given
    raise AttributeError("no bounds, wkt_geometry, point, tile or process bounds given.")
