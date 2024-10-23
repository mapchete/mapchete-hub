import logging
import os
import sys
from typing import Optional

from mapchete.log import all_mapchete_packages

from mapchete_hub.settings import LogLevels, mhub_settings


def setup_logger(
    log_level: Optional[LogLevels] = None, add_mapchete_logger: bool = False
):
    log_level = log_level or mhub_settings.log_level
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level.upper())
    logging.getLogger("mapchete_hub").addHandler(stream_handler)
    logging.getLogger("mapchete_hub").setLevel(log_level.upper())
    if (
        add_mapchete_logger
        or os.environ.get("MHUB_ADD_MAPCHETE_LOGGER", "").lower() == "true"
    ):
        for mapchete_package in all_mapchete_packages:
            logging.getLogger(mapchete_package).addHandler(stream_handler)
            logging.getLogger(mapchete_package).setLevel(log_level.upper())
