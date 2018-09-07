import logging
from ._core import mapchete_execute, mapchete_index, cleanup_config
from ._misc import send_to_queue, get_next_jobs, cleanup_datetime

__version__ = "0.1"


__all__ = [
    "mapchete_execute", "mapchete_index", "cleanup_config", "send_to_queue",
    "get_next_jobs", "cleanup_datetime"
]

# suppress spam loggers
SPAM_LOGGERS = ["botocore", "boto3", "rasterio", "smart_open", "urllib"]
for l in SPAM_LOGGERS:
    logging.getLogger(l).setLevel(logging.ERROR)
