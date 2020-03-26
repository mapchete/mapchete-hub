"""Default Flask and Celery configuration and related functions."""

import base64
from collections import OrderedDict
from contextlib import contextmanager
import datetime
import importlib
import logging
from mapchete.config import get_zoom_levels
from mapchete.errors import MapcheteProcessImportError
from mapchete.io.vector import reproject_geometry
from mapchete.tile import BufferedTilePyramid
import os
import py_compile
from shapely.geometry import box
from shapely import wkt
from tempfile import NamedTemporaryFile


logger = logging.getLogger(__name__)


def cleanup_datetime(d):
    """Convert datetime objects in dictionary to strings."""
    return OrderedDict(
        (k, cleanup_datetime(v)) if isinstance(v, dict)
        else (k, str(v)) if isinstance(v, datetime.date) else (k, v)
        for k, v in d.items()
    )


def process_area_from_config(
    mapchete_config=None,
    bounds=None,
    wkt_geometry=None,
    point=None,
    tile=None,
    zoom=None,
    dst_crs=None,
    **kwargs
):
    """
    Calculate process area from mapchete configuration and process parameters.

    Parameters
    ----------

    mapchete_config : dict
        A valid mapchete configuration.
    bounds : list
        Left, bottom, right, top coordinate of process area.
    point : list
        X and y coordinate of point over process tile.
    tile : list
        Zoom, row and column of process tile.
    wkt_geometry : str
        WKT representaion of process area.
    zoom : list or int
        Minimum and maximum zoom level or single zoom level.
    dst_crs : CRS
        CRS the process area is to be transformed to.

    Returns
    -------
    (geometry, geometry_process_crs) : tuple of shapely.Polygon
        Geometry in mhub CRS (which is defined in status_gpkg_profile) and in process CRS.
    """
    if not isinstance(mapchete_config, dict):
        raise TypeError("mapchete_config must be a dictionary")
    if "pyramid" not in mapchete_config:
        raise KeyError("mapchete_config has no 'pyramid' defined")

    tp = BufferedTilePyramid(
        mapchete_config["pyramid"]["grid"],
        metatiling=mapchete_config["pyramid"].get("metatiling", 1),
        pixelbuffer=mapchete_config["pyramid"].get("pixelbuffer", 0)
    )

    # bounds
    if bounds:
        geometry = box(*bounds)
    # wkt_geometry
    elif wkt_geometry:
        geometry = wkt.loads(wkt_geometry)
    # point
    elif point:
        x, y = point
        zoom_levels = get_zoom_levels(
            process_zoom_levels=mapchete_config["zoom_levels"],
            init_zoom_levels=zoom
        )
        geometry = tp.tile_from_xy(x, y, max(zoom_levels)).bbox
    # tile
    elif tile:
        geometry = tp.tile(*tile).bbox
    # mapchete_config
    elif mapchete_config.get("process_bounds"):
        geometry = box(*mapchete_config.get("process_bounds"))
    else:
        # raise error if no process areas is given
        raise AttributeError(
            "no bounds, wkt_geometry, point, tile or process bounds given."
        )
    # reproject geometry if necessary
    return reproject_geometry(
        geometry,
        src_crs=tp.crs,
        dst_crs=dst_crs or tp.crs
    ), geometry


@contextmanager
def custom_process_tempfile(mapchete_config):
    """
    Dump custom process in a temporary file and update configuration.

    This works only in case a custom process (i.e. raw python code) was passed on as a
    string in the "process" section. Otherwise it will return the configuration as is.

    Works as a context manager which removes temporary file on close.

    Examples
    --------
    >>> with custom_process_tempfile(mapchete_config) as config:
            # use config with mapchete
            with mapchete.open(config):
                ...
        # now, mapchete_config is reset to initial values and the tempfile is deleted


    Parameters
    ----------
    mapchete_config : dict
        A valid mapchete configuration.

    Yields
    ------
    mapchete_config : dict
        Modified mapchete config.
    """
    process = mapchete_config.get("process")

    if not process:
        raise MapcheteProcessImportError("no or empty process in configuration")

    try:
        # assume process module paths on successful import
        importlib.import_module(process)
        logger.debug("process module path found")
        yield mapchete_config

    except ImportError:
        # assume custom process: dump as temporary python file and update path
        with NamedTemporaryFile(suffix=".py") as temp_process_file:
            with open(temp_process_file.name, "w") as dst:
                logger.debug("dump custom process to %s" % temp_process_file.name)
                dst.write(base64.standard_b64decode(process).decode("utf-8"))
            # verify syntax is correct
            logger.debug("verifying syntax")
            py_compile.compile(temp_process_file.name, doraise=True)
            try:
                mapchete_config.update(process=temp_process_file.name)
                yield mapchete_config
            finally:
                mapchete_config.update(process=process)
        logger.debug("removed %s" % temp_process_file.name)


def _get_host_options():
    default = dict(host_ip="0.0.0.0", port=5000)
    return _get_opts(default)


def _get_flask_options():
    default = dict(
        broker_url="amqp://guest:guest@localhost:5672//",
        result_backend="rpc://guest:guest@localhost:5672//",
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
default_timeout = 5
