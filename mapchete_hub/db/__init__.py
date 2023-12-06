import mongomock

from mapchete_hub.db.memory import MemoryStatusHandler
from mapchete_hub.db.mongodb import MongoDBStatusHandler


class BackendDB:
    """Class to communicate with backend database."""

    def __new__(self, src=None):
        """Initialize."""
        if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
            return MongoDBStatusHandler(db_uri=src)
        elif isinstance(src, mongomock.database.Database):
            return MongoDBStatusHandler(database=src)
        elif isinstance(src, str) and src == "memory":
            return MemoryStatusHandler()
        else:  # pragma: no cover
            raise NotImplementedError(f"backend {src} of type {type(src)}")
