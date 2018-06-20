from billiard import cpu_count, current_process
from billiard.exceptions import WorkerLostError
from billiard.pool import Pool
from celery.utils.log import get_task_logger
from functools import partial
import mapchete
from mapchete.config import _map_to_new_config
from mapchete.errors import MapcheteNodataTile, MapcheteProcessException
from mapchete.index import zoom_index_gen
from mapchete.tile import BufferedTilePyramid
import os
import signal
import subprocess
import time

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
        num_processed = 0
        zoom_levels = list(_get_zoom_level(zoom, mp))
        assert zoom_levels
        total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
        yield total_tiles
        if total_tiles == 0:
            logger.debug("no tiles to be processed")
            return
        logger.debug(
            "run process on %s tiles using %s workers", total_tiles, multi)
        f = partial(_process_worker, mp)
        for zoom in zoom_levels:
            missing = set(mp.get_process_tiles(zoom))
            for attempt in range(max_attempts):
                logger.debug(
                    "attempt %s of %s to process %s tiles",
                    attempt + 1, max_attempts, len(missing)
                )
                if not missing:
                    logger.debug("all tiles processed")
                    break
                try:
                    pool = Pool(multi, _worker_sigint_handler)
                    for tile, message in pool.imap_unordered(
                        f, missing,
                        # set chunksize to between 1 and max_chunksize
                        chunksize=min([max([total_tiles // multi, 1]), max_chunksize])
                    ):
                        missing.discard(tile)
                        num_processed += 1
                        logger.debug("tile %s/%s finished", num_processed, total_tiles)
                        yield dict(process_tile=tile, **message)
                except KeyboardInterrupt:
                    logger.error("Caught KeyboardInterrupt")
                    raise
                except Exception as e:
                    if isinstance(e.args[0].type, type(WorkerLostError)):
                        logger.debug("Caught WorkerLostError")
                    else:
                        logger.exception(e)
                        raise
                finally:
                    logger.debug("terminate pool")
                    pool.terminate()
                    logger.debug("close pool")
                    pool.close()
                    logger.debug("join pool")
                    pool.join()
            if missing:
                logger.debug("missing tiles: %s", missing)
                raise MapcheteProcessException(
                    "not all tiles processed after %s retries", max_attempts
                )
        logger.debug("%s tile(s) iterated", (str(num_processed)))


def _process_worker(process, process_tile):
    """Worker function running the process."""
    logger.debug((process_tile.id, "running on %s" % current_process().name))

    # skip execution if overwrite is disabled and tile exists
    if process.config.mode == "continue" and (
        process.config.output.tiles_exist(process_tile)
    ):
        logger.debug((process_tile.id, "tile exists, skipping"))
        return process_tile, dict(
            process="output already exists",
            write="nothing written")

    # execute on process tile
    else:
        start = time.time()
        try:
            output = process.execute(process_tile, raise_nodata=True)
        except MapcheteNodataTile:
            output = None
        processor_message = "processed in %ss" % round(time.time() - start, 3)
        logger.debug((process_tile.id, processor_message))
        writer_message = process.write(process_tile, output)
        return process_tile, dict(
            process=processor_message,
            write=writer_message
        )


def _worker_sigint_handler():
    # ignore SIGINT and let everything be handled by parent process
    signal.signal(signal.SIGINT, signal.SIG_IGN)


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
