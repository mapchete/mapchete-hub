from celery.signals import after_setup_logger
import logging

from mapchete.log import (
    all_mapchete_packages,
    key_value_replace_patterns,
    KeyValueFilter
)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')


def _setup_loggers():
    all_mapchete_packages.add("mapchete_hub")
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.WARNING)
    stream_handler.addFilter(KeyValueFilter(key_value_replace=key_value_replace_patterns))
    for i in all_mapchete_packages:
        logging.getLogger(i).addHandler(stream_handler)

# setup loggers on module load to assert logging is confiruged in monitor
_setup_loggers()


@after_setup_logger.connect
def setup_loggers(*args, **kwargs):
    """Explicitly set up loggers again afert Celery messed around with logging."""
    _setup_loggers()


def set_log_level(loglevel, *args, **kwargs):
    """Set log level of all registered mapchete packages."""
    stream_handler.setLevel(loglevel)
    for i in all_mapchete_packages:
        logging.getLogger(i).setLevel(loglevel)


def setup_logfile(logfile):
    """Setup logfile in DEBUG mode."""
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(KeyValueFilter(key_value_replace=key_value_replace_patterns))
    for i in all_mapchete_packages:
        logging.getLogger(i).addHandler(file_handler)
        logging.getLogger(i).setLevel(logging.DEBUG)
