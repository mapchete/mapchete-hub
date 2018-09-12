from multiprocessing import cpu_count
from celery.utils.log import get_task_logger
import mapchete
from mapchete.config import _map_to_new_config
from mapchete.index import zoom_index_gen
from mapchete.tile import BufferedTilePyramid
import os
import subprocess


from mapchete_hub.config import main_options


logger = get_task_logger(__name__)


def cleanup_config(mp_config):
    return {k: v for k, v in mp_config.items() if not k.startswith('mhub_')}


def mapchete_index(
    config=None,
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
    for_gdal=True
):
    config.update(config_dir=main_options['config_dir'])
    if not any([geojson, gpkg, shapefile, txt]):
        raise ValueError(
            "one of 'geojson', 'gpkg', 'shapefile' or 'txt' must be provided")
    if not out_dir:
        raise ValueError('no out_dir given')

    def _gpkg_to_shp(zoom):
        src = os.path.join(out_dir, zoom + ".gpkg")
        dst = os.path.join(out_dir, zoom + ".shp")
        sp = subprocess.run(
            ["ogr2ogr", dst, src],
            stdout=subprocess.PIPE
        )
        if sp.returncode:
            logger.error("ogr2ogr error when converting %s to %s", src, dst)

    # process single tile
    if tile:
        conf = _map_to_new_config(config)
        tile = BufferedTilePyramid(
            conf["pyramid"]["grid"],
            metatiling=conf["pyramid"].get("metatiling", 1),
            pixelbuffer=conf["pyramid"].get("pixelbuffer", 0)
        ).tile(*tile)
        with mapchete.open(
            config, mode="readonly", bounds=tile.bounds,
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
            if gpkg and not shapefile:
                _gpkg_to_shp(tile.zoom)

    else:
        if process_area:
            bounds = process_area.bounds
        else:
            bounds = bounds
        with mapchete.open(
            config, mode="readonly", zoom=zoom, bounds=bounds
        ) as mp:
            num_processed = 0
            logger.debug("process bounds: %s", mp.config.init_bounds)
            logger.debug("process zooms: %s", mp.config.init_zoom_levels)
            logger.debug("fieldname: %s", fieldname)
            zoom_levels = list(_get_zoom_level(zoom, mp))
            assert zoom_levels
            total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
            yield total_tiles
            if total_tiles == 0:
                return
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
            if gpkg and not shapefile:
                _gpkg_to_shp(z)


def mapchete_execute(
    config=None,
    mode="continue",
    zoom=None,
    process_area=None,
    multi=cpu_count(),
    max_chunksize=1,
    max_attempts=20
):
    if config is None:
        raise AttributeError("no mapchete config given")
    config.update(config_dir=main_options['config_dir'])

    with mapchete.open(config, mode=mode, zoom=zoom, bounds=process_area.bounds) as mp:
        logger.debug("run with multiprocessing")
        zoom_levels = list(_get_zoom_level(zoom, mp))
        assert zoom_levels
        total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
        yield total_tiles
        if total_tiles == 0:
            logger.debug("no tiles to be processed")
            return
        for process_info in mp.batch_processor(
            zoom=zoom, multi=multi, max_chunksize=max_chunksize
        ):
            yield process_info


def _get_zoom_level(zoom, process):
    """Determine zoom levels."""
    if zoom is None:
        return reversed(process.config.zoom_levels)
    if isinstance(zoom, int):
        return [zoom]
    elif len(zoom) == 2:
        return reversed(range(min(zoom), max(zoom)+1))
    elif len(zoom) == 1:
        return zoom
