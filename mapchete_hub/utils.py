import base64
from collections import OrderedDict, ValuesView
from contextlib import contextmanager
import datetime
import importlib
import json
import logging
from mapchete.config import get_zoom_levels
from mapchete.errors import MapcheteProcessImportError
from mapchete.io.vector import reproject_geometry
from mapchete.tile import BufferedTilePyramid
import py_compile
from rasterio.crs import CRS
from shapely.geometry import box, mapping, shape
from tempfile import NamedTemporaryFile
import uuid


logger = logging.getLogger(__name__)


def cleanup_datetime(d):
    """Convert datetime objects in dictionary to strings."""
    return OrderedDict(
        (k, cleanup_datetime(v)) if isinstance(v, dict)
        else (k, str(v)) if isinstance(v, datetime.date) else (k, v)
        for k, v in d.items()
    )


def process_area_from_config(
    config=None,
    params=None,
    dst_crs=None,
    **kwargs
):
    """
    Calculate process area from mapchete configuration and process parameters.

    Parameters
    ----------

    config : dict
        A valid mapchete configuration.
    params : dict
        Additional process parameters:

        point : list
            X and y coordinate of point over process tile.
        tile : list
            Zoom, row and column of process tile.
        geometry : dict
            GeoJSON representaion of process area.
        zoom : list or int
            Minimum and maximum zoom level or single zoom level.
    dst_crs : CRS
        CRS the process area is to be transformed to.

    Returns
    -------
    (geometry, geometry_process_crs) : tuple of shapely.Polygon
        Geometry in mhub CRS (which is defined in status_gpkg_profile) and in process CRS.
    """
    params = params or dict()
    if not isinstance(config, dict):
        raise TypeError("mapchete_config must be a dictionary")
    if "pyramid" not in config:
        raise KeyError("mapchete_config has no 'pyramid' defined")

    tp = BufferedTilePyramid(
        config["pyramid"]["grid"],
        metatiling=config["pyramid"].get("metatiling", 1),
        pixelbuffer=config["pyramid"].get("pixelbuffer", 0)
    )

    # bounds
    if params.get("bounds"):
        geometry = box(*params.get("bounds"))
    # geometry
    elif params.get("geometry"):
        geometry = shape(params.get("geometry"))
    # point
    elif params.get("point"):
        x, y = params.get("point")
        zoom_levels = get_zoom_levels(
            process_zoom_levels=config["zoom_levels"],
            init_zoom_levels=params.get("zoom")
        )
        geometry = tp.tile_from_xy(x, y, max(zoom_levels)).bbox
    # tile
    elif params.get("tile"):
        geometry = tp.tile(*params.get("tile")).bbox
    # mapchete_config
    elif config.get("process_bounds"):
        geometry = box(*config.get("process_bounds"))
    else:
        # raise error if no process areas is given
        raise AttributeError(
            "no bounds, geometry, point, tile or process bounds given."
        )

    # reproject geometry if necessary and return original geometry
    return reproject_geometry(
        geometry,
        src_crs=tp.crs,
        dst_crs=CRS.from_user_input(dst_crs) if dst_crs else tp.crs
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


def parse_jobs_for_backend(raw, init_job_id=None, dst_crs=None):
    """Parse job JSON into chainable representation for Celery."""
    init_job_id = init_job_id or uuid.uuid4().hex

    def _to_list(data):
        if isinstance(data, dict):
            logger.debug("single job received")
            return [data]
        elif isinstance(data, (list, tuple, ValuesView)):
            logger.debug("batch job received")
            return list(data)
        elif isinstance(data, str):
            return _to_list(json.loads(raw))
        else:  # pragma: no cover
            raise TypeError("""Input must be dictionary or list of dictionaries.""")

    # load JSON if necessary and convert dict into list of dicts if batch job
    jobs = _to_list(raw)

    # get process area in mhub backend CRS and process CRS
    process_area, process_area_process_crs = process_area_from_config(
        **jobs[0], dst_crs=dst_crs
    )

    def _verify_job(job, job_id=None, previous_job_id=None, next_job_id=None):
        job_name = job["params"].get("job_name", "unnamed_job")

        # check mapchete configuration
        if "config" not in job:
            raise KeyError("mapchete config not provided")
        if not isinstance(job["config"], dict):
            raise TypeError(
                "{}: mapchete config must be a dictionary, not {}".format(
                    job_name, type(job["config"])
                )
            )

        # verify process code
        # by calling this context manager, a syntax check and import will be conducted
        # TODO maby a bad idea to run this on the server
        with custom_process_tempfile(job["config"]):
            pass

        # process mode
        mode = job["params"].get("mode", "continue")
        if mode not in ["continue", "overwrite"]:
            raise ValueError(
                "{}: mode must be one of continue, overwrite, not {}".format(
                    job_name, mode
                )
            )

        # mapchete hub command
        if not job.get("command", None):
            raise KeyError("{}: no command given".format(job_name))

        # mapchete hub queue
        queue = job["params"].get("queue") or "{}_queue".format(job["command"])

        # dict for celery task
        kwargs = dict(
            job_id=job_id,
            command=job["command"],
            params=job["params"],
            config=cleanup_datetime(job["config"]),
            previous_job_id=previous_job_id,
            next_job_id=next_job_id,
            process_area=mapping(process_area),
            process_area_process_crs=mapping(process_area_process_crs),
        )

        # dict for the celery task call
        return dict(
            task_id=job_id,
            command=job["command"],
            queue=queue,
            args=(None, ),
            kwargs=kwargs,
            kwargsrepr=json.dumps(kwargs)
        )

    job_ids = [
        None,
        init_job_id,
        *[uuid.uuid4().hex for _ in range(len(jobs) - 1)],
        None
    ]
    return [
        _verify_job(
            job,
            job_id=job_ids[i + 1],
            previous_job_id=job_ids[i],
            next_job_id=job_ids[i + 2]
        )
        for i, job in enumerate(jobs)
    ]
