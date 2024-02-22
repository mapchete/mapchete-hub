from contextlib import contextmanager
from typing import Any, Generator

import mongomock

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.db.memory import MemoryStatusHandler
from mapchete_hub.db.mongodb import MongoDBStatusHandler


@contextmanager
def init_backenddb(src: Any) -> Generator[BaseStatusHandler, None, None]:
    if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
        with MongoDBStatusHandler(db_uri=src) as db:
            yield db
    elif isinstance(src, mongomock.database.Database):
        with MongoDBStatusHandler(database=src) as db:
            yield db
    elif isinstance(src, str) and src == "memory":
        with MemoryStatusHandler() as db:
            yield db
    else:  # pragma: no cover
        raise NotImplementedError(f"backend {src} of type {type(src)}")
