"""Example process file."""
import ctypes
import logging

logger = logging.getLogger(__name__)


def execute(mp):
    """User defined process."""
    if mp.tile.id == (11, 253, 520):
        logger.debug("force segfault")
        ctypes.string_at(0)
    else:
        return "empty"
