"""Example process file."""
from billiard.exceptions import WorkerLostError


def execute(mp):
    """User defined process."""
    raise WorkerLostError("test")
