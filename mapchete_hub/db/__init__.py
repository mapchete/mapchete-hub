from typing import Any

import mongomock

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.db.memory import MemoryStatusHandler
from mapchete_hub.db.mongodb import MongoDBStatusHandler


def init_backenddb(src: Any) -> BaseStatusHandler:
    if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
        return MongoDBStatusHandler(db_uri=src)
    elif isinstance(src, mongomock.database.Database):
        return MongoDBStatusHandler(database=src)
    elif isinstance(src, str) and src == "memory":
        return MemoryStatusHandler()
    else:  # pragma: no cover
        raise NotImplementedError(f"backend {src} of type {type(src)}")
