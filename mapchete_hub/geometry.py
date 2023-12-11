"""
Geometry functions.
"""
from mapchete.config.parse import get_zoom_levels
from mapchete.io.vector import fiona_open, reproject_geometry
from mapchete.path import MPath
from mapchete.tile import BufferedTilePyramid
from rasterio.crs import CRS
from shapely import from_wkt, intersection_all
from shapely.geometry import box, mapping, shape
from shapely.ops import cascaded_union

from mapchete_hub.models import MapcheteJob


def process_area_from_config(job: MapcheteJob, dst_crs=None, **kwargs):
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
    tp = BufferedTilePyramid(**dict(job.config.pyramid))
    area = job.params.get("area")
    area_path = MPath.from_inp(area) if area else None
    # bounds and area
    if job.params.get("bounds") and job.params.get("area"):
        geometry_bounds = box(*job.params.get("bounds"))
        if area_path and area_path.exists():
            all_geoms = []
            with fiona_open(area_path, mode="r") as src:
                for s in src:
                    all_geoms.append(shape(s["geometry"]))
            geometry_area = cascaded_union(all_geoms)
        else:
            geometry_area = from_wkt(job.params.get("area"))
        geometry = intersection_all([geometry_bounds, geometry_area])
    # bounds
    elif job.params.get("bounds"):
        geometry = box(*job.params.get("bounds"))
    # geometry
    elif job.params.get("geometry"):
        geometry = shape(job.params.get("geometry"))
    # area
    elif job.params.get("area"):
        if area_path and area_path.exists():
            all_geoms = []
            with fiona_open(area_path, mode="r") as src:
                for s in src:
                    all_geoms.append(shape(s["geometry"]))
            geometry = cascaded_union(all_geoms)
        else:
            geometry = from_wkt(job.params.get("area"))
    # point
    elif job.params.get("point"):
        x, y = job.params.get("point")
        zoom_levels = get_zoom_levels(
            process_zoom_levels=job.config.zoom_levels,
            init_zoom_levels=job.params.get("zoom"),
        )
        geometry = tp.tile_from_xy(x, y, max(zoom_levels)).bbox
    # tile
    elif job.params.get("tile"):
        geometry = tp.tile(*job.params.get("tile")).bbox
    # mapchete_config
    elif job.config.bounds and job.config.area:
        geometry_bounds = box(*job.config.get("bounds"))
        if area_path and area_path.exists():
            all_geoms = []
            with fiona_open(area_path, mode="r") as src:
                for s in src:
                    all_geoms.append(shape(s["geometry"]))
            geometry_area = cascaded_union(all_geoms)
        else:
            geometry_area = from_wkt(job.params.get("area"))
        geometry = intersection_all([geometry_bounds, geometry_area])
    elif job.config.bounds:
        geometry = box(*job.config.bounds)
    elif job.config.area:
        if area_path and area_path.exists():
            all_geoms = []
            with fiona_open(area_path, mode="r") as src:
                for s in src:
                    all_geoms.append(shape(s["geometry"]))
            geometry = cascaded_union(all_geoms)
        else:
            geometry = from_wkt(job.config.area)
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
