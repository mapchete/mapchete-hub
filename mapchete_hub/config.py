"""Default Flask and Celery configuration and related functions."""


from collections import OrderedDict
import datetime
from mapchete.config import get_zoom_levels
from mapchete.tile import BufferedTilePyramid
import os
from shapely.geometry import box
from shapely import wkt


def cleanup_datetime(d):
    """Represent timestamps as strings, not datetime.date objects."""
    return OrderedDict(
        (k, cleanup_datetime(v)) if isinstance(v, dict)
        else (k, str(v)) if isinstance(v, datetime.date) else (k, v)
        for k, v in d.items()
    )


def process_area_from_config(config):
    """Calculate process area from process config."""
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
            init_zoom_levels=config.get("zoom")
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


def _get_host_options():
    default = dict(host_ip="0.0.0.0", port=5000)
    return _get_opts(default)


def _get_flask_options():
    default = dict(
        broker_url="amqp://guest:guest@localhost:5672//",
        result_backend="rpc://guest:guest@localhost:5672//",
        # required to hanlde exceptions raised by billiard
        result_serializer="json",
        task_serializer="json",
        event_serializer="json",
        accept_content=["json"],
        task_routes={
            "mapchete_hub.commands.execute.*": {"queue": "execute_queue"},
            "mapchete_hub.commands.index.*": {"queue": "index_queue"},
        },
        task_acks_late=True,
        worker_send_task_events=True,
        worker_hijack_root_logger=False,
        task_send_sent_event=True,
        event_queue_expires=604800,  # one week in seconds
    )
    opts = {}
    for k, v in _get_opts(default).items():
        opts[k] = v
        opts["CELERY_" + k.upper()] = v
    return opts


def _get_main_options():
    default = dict(
        config_dir="/tmp/",
        status_gpkg="status.gpkg",
        status_gpkg_profile=dict(
            crs={"init": "epsg:4326"},
            driver="GPKG",
            schema=dict(
                geometry="Polygon",
                properties=dict(
                    command="str:20",
                    config="str:1000",
                    exception="str:100",
                    hostname="str:50",
                    job_id="str:100",
                    job_name="str:100",
                    parent_job_id="str:100",
                    child_job_id="str:100",
                    progress_data="str:100",
                    queue="str:50",
                    runtime="float",
                    started="float",
                    state="str:50",
                    timestamp="float",
                    traceback="str:1000",
                )
            )
        ),
    )
    return _get_opts(default)


def _get_opts(default):
    """
    Get mhub config options from environement.

    Use environmental variables starting with "MHUB_", otherwise fall back to default
    values.
    """
    return {
        k: os.environ.get("MHUB_" + k.upper(), default.get(k)) for k in default.keys()
    }


host_options = _get_host_options()
flask_options = _get_flask_options()
main_options = _get_main_options()
timeout = 5
