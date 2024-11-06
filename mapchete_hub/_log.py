import logging
import sys
from typing import Any, Dict, Optional

from mapchete.log import all_mapchete_packages
from uvicorn.config import LOGGING_CONFIG

from mapchete_hub.settings import LogLevels, mhub_settings


def setup_logger(
    log_level: Optional[LogLevels] = None,
    add_mapchete_logger: bool = False,
    log_format: str = "%(asctime)s %(levelname)s %(name)s %(message)s",
):
    log_level = log_level or mhub_settings.log_level
    add_mapchete_logger = add_mapchete_logger or mhub_settings.add_mapchete_logger

    # setup stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format))
    stream_handler.setLevel(log_level.upper())

    # determine which package loggers to set up
    mapchete_packages = ["mapchete_hub"]
    if add_mapchete_logger:
        mapchete_packages.extend(all_mapchete_packages)

    # add stream handler & set log levels on package loggers
    for mapchete_package in mapchete_packages:
        logging.getLogger(mapchete_package).addHandler(stream_handler)
        logging.getLogger(mapchete_package).setLevel(log_level.upper())


def uvicorn_log_config(
    log_level: Optional[LogLevels] = None,
    add_mapchete_logger: bool = False,
    log_format: str = "%(asctime)s %(levelname)s %(name)s %(message)s",
) -> Dict[str, Any]:
    log_level = log_level or mhub_settings.log_level
    add_mapchete_logger = add_mapchete_logger or mhub_settings.add_mapchete_logger

    # setup log config
    log_config = LOGGING_CONFIG.copy()
    for formatter in ["access", "default"]:
        log_config["formatters"][formatter]["fmt"] = log_format
    cfg = dict(handlers=["default"], level=log_level.upper())

    # determine which package loggers to set up
    mapchete_packages = ["mapchete_hub"]
    if add_mapchete_logger:
        mapchete_packages.extend(all_mapchete_packages)

    # add package loggers & their configuration
    for mapchete_package in mapchete_packages:
        log_config["loggers"][mapchete_package] = cfg

    return log_config
