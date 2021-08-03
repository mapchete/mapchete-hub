from datetime import datetime
import logging
import mongomock
from pydantic import NonNegativeInt
import pymongo
from shapely.geometry import box, mapping, Polygon
import time
from uuid import uuid4

from mapchete_hub import models
from mapchete_hub.geometry import process_area_from_config

logger = logging.getLogger(__name__)


class BackendDB():
    """Class to communicate with backend database."""

    def __new__(self, src=None):
        """Initialize."""
        if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
            return MongoDBStatusHandler(db_uri=src)
        elif isinstance(src, (pymongo.MongoClient, mongomock.MongoClient)):
            return MongoDBStatusHandler(client=src)
        elif isinstance(src, mongomock.database.Database):
            return MongoDBStatusHandler(database=src)
        else:  # pragma: no cover
            raise NotImplementedError(f"backend {src} of type {type(src)}")


class MongoDBStatusHandler():
    """Abstraction layer over MongoDB backend."""

    def __init__(self, db_uri=None, client=None, database=None):
        """Initialize."""
        if db_uri:  # pragma: no cover
            logger.debug(f"connect to MongoDB: {db_uri}")
            self._client = pymongo.MongoClient(db_uri, tz_aware=True)
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif client:
            logger.debug(f"use existing PyMongo client instance: {client}")
            self._client = client
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif database:
            self._client = None
            self._db = database
            self._jobs = self._db["jobs"]
        logger.debug(f"active client {self._client}")

    def jobs(self, **kwargs):
        """
        Return jobs as list of GeoJSON features.

        Parameters
        ----------
        output_path : str
            Filter by output path.
        state : str
            Filter by job state.
        command : str
            Filter by mapchete Hub command.
        queue : str
            Filter by queue.
        job_name : str
            Filter by job name.
        bounds : list or tuple
            Filter by spatial bounds.
        from_date : str
            Filter by earliest date.
        to_date : str
            Filter by latest date.

        Returns
        -------
        GeoJSON features : list of dict
        """
        query = {k: v for k, v in kwargs.items() if v is not None}
        logger.debug(f"raw query: {query}")

        # parsing job state groups and job states
        if query.get("state") is not None:
            state = models.State[query.get("state")]
            # group states are lowercase!
            query.update(state={"$in": [state]})

        # convert bounds query into a geo search query
        if query.get("bounds") is not None:
            query.update(
                geometry={
                    "$geoIntersects": {"$geometry": mapping(box(*query.get("bounds")))}
                }
            )
            query.pop("bounds")

        # convert from_date and to_date kwargs to timestamp query
        if query.get("from_date") or query.get("to_date"):
            query.update(
                timestamp={
                    k: datetime.timestamp(v) for k, v in zip(
                        ["$gte", "$lt"],
                        [query.get("from_date"), query.get("to_date")]
                    )
                    if v is not None
                }
            )
            query.pop("from_date", None)
            query.pop("to_date", None)

        logger.debug(f"MongoDB query: {query}")
        return [
            self._entry_to_geojson(e)
            for e in self._jobs.find(query)
        ]

    def job(self, job_id):
        """
        Return job as GeoJSON feature.

        Parameters
        ----------
        job_id : str
            Unique job ID.

        Returns
        -------
        GeoJSON feature or None
        """
        result = self._jobs.find_one({"job_id": job_id})
        if result:
            return self._entry_to_geojson(result)
        else:
            raise KeyError(f"job {job_id} not found in the database: {result}")

    def new(self, job_config: models.MapcheteJob = None):
        """
        Create new job entry in database.
        """
        job_id = uuid4().hex
        logger.debug(f"got new job with config {job_config} and assigning job ID {job_id}")
        entry = models.Job(
            job_id=job_id,
            state=models.State["pending"],
            geometry=process_area_from_config(job_config, dst_crs="EPSG:4326")[0],
            mapchete=job_config,
            output_path=job_config.dict()["config"]["output"]["path"]
        )
        logger.debug(entry)
        result = self._jobs.insert_one(entry.dict())
        logger.debug(result)
        if result.acknowledged:
            return self.job(job_id)
            # return self._entry_to_geojson(job)
        else:
            raise RuntimeError(f"entry {entry} could not be inserted into MongoDB")

    def set(
        self,
        job_id: str = None,
        state: models.State = None,
        current_progress: NonNegativeInt = None,
        total_progress: NonNegativeInt= None,
        exception: str = None
    ):
        entry = {"job_id": job_id}
        if state is not None:
            entry.update(state=models.State[state])
        if current_progress is not None:
            entry.update(current_progress=current_progress)
        if total_progress is not None:
            entry.update(total_progress=total_progress)
        if exception is not None:
            entry.update(exception=str(exception))
        logger.debug(f"upsert entry: {entry}")
        return self._entry_to_geojson(
            self._jobs.find_one_and_update(
                {"job_id": job_id},
                {"$set": entry},
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER
            )
        )

    def _entry_to_geojson(self, entry):
        return {
            "type": "Feature",
            "id": str(entry["job_id"]),
            "geometry": entry["geometry"],
            "properties": {
                k: entry.get(k)
                for k in entry.keys()
                if k not in ["job_id", "geometry", "id", "_id"]
            }
        }

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        pass
