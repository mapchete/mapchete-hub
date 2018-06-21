"""Example process file."""
from billiard.exceptions import WorkerLostError
from random import randint


def execute(mp):
    """User defined process."""
    if not randint(0, 5) or mp.tile.id == (11, 253, 520):
        raise WorkerLostError("test")
    else:
        return "empty"
