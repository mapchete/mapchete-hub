import billiard
from billiard import cpu_count
from collections import OrderedDict
import logging
import mapchete
from mapchete.config import get_zoom_levels

from mapchete_hub.config import get_mhub_config
from mapchete_hub.utils import custom_process_tempfile


logger = logging.getLogger(__name__)


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
        Area to be processed as shapely.Geometry.
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
    with custom_process_tempfile(mapchete_config) as tmpfile_config:
        with mapchete.Timer() as t:
            with mapchete.open(
                OrderedDict(
                    tmpfile_config,
                    config_dir=get_mhub_config().CONFIG_DIR
                ),
                mode=mode or "continue",
                zoom=zoom,
                bounds=process_area.bounds
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
