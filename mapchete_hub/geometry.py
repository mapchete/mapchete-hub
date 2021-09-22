from mapchete.config import get_zoom_levels
from mapchete.io.vector import reproject_geometry
from mapchete.tile import BufferedTilePyramid
from rasterio.crs import CRS
from shapely.geometry import box, mapping, shape

from mapchete_hub import models


def process_area_from_config(job_config: models.MapcheteJob, dst_crs=None, **kwargs):
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
    job_config = (
        models.MapcheteJob(**job_config) if isinstance(job_config, dict) else job_config
    )
    config = job_config.dict().get("config") or {}
    params = job_config.dict().get("params") or {}

    if "pyramid" not in config:
        raise KeyError("mapchete_config has no 'pyramid' defined")

    tp = BufferedTilePyramid(
        config["pyramid"]["grid"],
        metatiling=config["pyramid"].get("metatiling", 1),
        pixelbuffer=config["pyramid"].get("pixelbuffer", 0),
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
            init_zoom_levels=params.get("zoom"),
        )
        geometry = tp.tile_from_xy(x, y, max(zoom_levels)).bbox
    # tile
    elif params.get("tile"):
        geometry = tp.tile(*params.get("tile")).bbox
    # mapchete_config
    elif config.get("bounds"):
        geometry = box(*config.get("bounds"))
    else:
        # raise error if no process areas is given
        raise AttributeError(
            "no bounds, geometry, point, tile or process bounds given."
        )

    # reproject geometry if necessary and return original geometry
    return (
        mapping(
            reproject_geometry(
                geometry,
                src_crs=tp.crs,
                dst_crs=CRS.from_user_input(dst_crs) if dst_crs else tp.crs,
            )
        ),
        mapping(geometry),
    )
