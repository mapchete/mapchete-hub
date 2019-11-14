import billiard
from billiard import cpu_count
import logging
import mapchete
from mapchete.config import _map_to_new_config, get_zoom_levels
from mapchete.index import zoom_index_gen
from mapchete.tile import BufferedTilePyramid
from shapely import wkt

from mapchete_hub.config import main_options


logger = logging.getLogger(__name__)


def cleanup_config(mp_config):
    """Strip configuration from all mapchete Hub items."""
    return {k: v for k, v in mp_config.items() if not k.startswith('mhub_')}


def mapchete_index(
    mapchete_config=None,
    process_area=None,
    bounds=None,
    tile=None,
    zoom=None,
    geojson=False,
    gpkg=False,
    shapefile=False,
    txt=False,
    out_dir=None,
    fieldname='location',
    basepath=None,
    for_gdal=True,
    **kwargs
):
    """
    Wrapper around index generation method which behaves like `mapchete index`.

    Parameters
    ----------
    mapchete_config : dict
        A valid Mapchete configuration.
    process_area : str
        Area to be processed as WKT.
    bounds : tuple
        Bounds to be processed.
    tile : tuple or Tile
        Tile to be processed.
    zoom : int or list of ints
        Zoom levels to be processed.
    geojson : bool
        generate GeoJSON index (default: False)
    gpkg : bool
        generate GeoPackage index (default: False)
    shapefile : bool
        generate Shapefile index (default: False)
    txt : bool
        generate tile path list textfile (default: False)
    vrt : bool
        GDAL-style VRT file (default: False)
    fieldname : str
        field name which contains paths of tiles (default: "location")
    basepath : str
        if set, use custom base path instead of output path
    for_gdal : bool
        use GDAL compatible remote paths, i.e. add "/vsicurl/" before path
        (default: True)

    Yields
    ------
    First item is an integer indicating number of tiles to be processed.
    Following items are ProcessInfo objects containing process and write information for
    each process tile.
    """
    if not any([geojson, gpkg, shapefile, txt]):
        raise ValueError(
            "one of 'geojson', 'gpkg', 'shapefile' or 'txt' must be provided")
    if not out_dir:
        raise ValueError('no out_dir given')

    # process single tile
    if tile:
        tile = BufferedTilePyramid.from_dict(
            _map_to_new_config(mapchete_config)["pyramid"]
        ).tile(*tile)
        with mapchete.open(
            dict(mapchete_config, config_dir=main_options['config_dir']),
            mode="readonly",
            bounds=tile.bounds,
            zoom=tile.zoom
        ) as mp:
            num_processed = 0
            total_tiles = mp.count_tiles(tile.zoom, tile.zoom)
            yield total_tiles
            for tile in zoom_index_gen(
                mp=mp,
                zoom=tile.zoom,
                out_dir=out_dir,
                geojson=geojson,
                gpkg=gpkg,
                shapefile=shapefile,
                txt=txt,
                fieldname=fieldname,
                basepath=basepath,
                for_gdal=for_gdal
            ):
                num_processed += 1
                logger.debug("tile %s/%s finished", num_processed, total_tiles)
                yield dict(process_tile=tile)

    else:
        with mapchete.open(
            dict(mapchete_config, config_dir=main_options['config_dir']),
            mode="readonly",
            zoom=zoom,
            bounds=wkt.loads(process_area).bounds if process_area else bounds
        ) as mp:
            num_processed = 0
            logger.debug("process bounds: %s", mp.config.init_bounds)
            logger.debug("process zooms: %s", mp.config.init_zoom_levels)
            logger.debug("fieldname: %s", fieldname)
            zoom_levels = get_zoom_levels(
                process_zoom_levels=mp.config.zoom_levels,
                init_zoom_levels=zoom
            )
            total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
            yield total_tiles
            if total_tiles:
                for z in mp.config.init_zoom_levels:
                    logger.debug("zoom %s", z)
                    for tile in zoom_index_gen(
                        mp=mp,
                        zoom=z,
                        out_dir=out_dir,
                        geojson=geojson,
                        gpkg=gpkg,
                        shapefile=shapefile,
                        txt=txt,
                        fieldname=fieldname,
                        basepath=basepath,
                        for_gdal=for_gdal
                    ):
                        num_processed += 1
                        logger.debug("tile %s/%s finished", num_processed, total_tiles)
                        yield dict(process_tile=tile)


def mapchete_execute(
    mapchete_config=None,
    mode=None,
    zoom=None,
    process_area=None,
    multi=cpu_count(),
    max_chunksize=1,
    **kwargs
):
    """
    Wrapper around `mp.batch_processor()` method which behaves like `mapchete execute`.

    Parameters
    ----------
    mapchete_config : dict
        A valid Mapchete configuration.
    mode : string
        Process mode. Either "continue" or "overwrite".
    zoom : int or list of ints
        Zoom levels to be processed.
    process_area : str
        Area to be processed as WKT.
    multi : int
        Number of CPU cores to be used. Default is number of available cores.
    max_chunksize : int
        Number of tasks to be passed on to a billiard worker at once.

    Yields
    ------
    First item is an integer indicating number of tiles to be processed.
    Following items are ProcessInfo objects containing process and write information for
    each process tile.
    """
    with mapchete.Timer() as t:
        with mapchete.open(
            dict(mapchete_config, config_dir=main_options['config_dir']),
            mode=mode or "continue",
            zoom=zoom,
            bounds=wkt.loads(process_area).bounds
        ) as mp:
            zoom_levels = get_zoom_levels(
                process_zoom_levels=mp.config.zoom_levels,
                init_zoom_levels=zoom
            )
            total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
            yield total_tiles
            if total_tiles:
                logger.debug(
                    "run process on %s tiles using %s workers", total_tiles, multi
                )
                # run process on tiles
                for process_info in mp.batch_processor(
                    multiprocessing_module=billiard,
                    multi=multi,
                    zoom=zoom,
                    max_chunksize=max_chunksize
                ):
                    yield process_info

    logger.debug("processing finished in %s" % t)
