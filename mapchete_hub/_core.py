from billiard import cpu_count, current_process
from billiard.pool import Pool
from celery.utils.log import get_task_logger
from functools import partial
import mapchete
from mapchete.errors import MapcheteNodataTile
import time

from mapchete_hub.config import get_main_options


logger = get_task_logger(__name__)


def mapchete_execute(
    config=None,
    mode="continue",
    zoom=None,
    bounds=None,
    multi=cpu_count(),
    max_chunksize=1
):
    if config is None:
        raise AttributeError("no mapchete config given")
    config.update(config_dir=get_main_options()['config_dir'])

    with mapchete.open(config, mode=mode, zoom=zoom, bounds=bounds) as mp:
        logger.debug("run with multiprocessing")
        num_processed = 0
        zoom_levels = list(_get_zoom_level(zoom, mp))
        assert zoom_levels
        total_tiles = mp.count_tiles(min(zoom_levels), max(zoom_levels))
        yield total_tiles
        logger.debug(
            "run process on %s tiles using %s workers", total_tiles, multi)
        f = partial(_process_worker, mp)
        for zoom in zoom_levels:
            try:
                pool = Pool(multi)
                for tile, message in pool.imap_unordered(
                    f,
                    mp.get_process_tiles(zoom),
                    # set chunksize to between 1 and max_chunksize
                    chunksize=min([max([total_tiles // multi, 1]), max_chunksize])
                ):
                    num_processed += 1
                    logger.debug("tile %s/%s finished", num_processed, total_tiles)
                    yield dict(process_tile=tile, **message)
            except KeyboardInterrupt:
                logger.error("Caught KeyboardInterrupt, terminating workers")
                raise
            except Exception as e:
                logger.exception(e)
                raise
            finally:
                logger.debug("close pool")
                pool.close()
                logger.debug("join pool")
                pool.join()
            # for tile in mp.get_process_tiles(zoom):
            #     yield dict(process_tile=tile, **_process_worker(mp, tile)[1])
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
