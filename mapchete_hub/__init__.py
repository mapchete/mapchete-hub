import logging
from ._core import mapchete_execute, mapchete_index, cleanup_config
from ._misc import send_to_queue, get_next_jobs, cleanup_datetime

__version__ = "0.1"


__all__ = [
    "mapchete_execute", "mapchete_index", "cleanup_config", "send_to_queue",
    "get_next_jobs", "cleanup_datetime"
]

# suppress spam loggers
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("smart_open").setLevel(logging.ERROR)
