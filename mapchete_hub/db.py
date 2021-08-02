from datetime import datetime
import logging
import mongomock.collection
import mongomock.database
import pymongo
from shapely.geometry import box, mapping, Polygon
import time

from mapchete_hub import models

logger = logging.getLogger(__name__)


class BackendDB():
    """Class to communicate with backend database."""

    def __new__(self, src=None):
        """Initialize."""
        if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
            return MongoDBStatusHandler(db_uri=src)
        elif isinstance(src, (pymongo.MongoClient, mongomock.MongoClient)):
            return MongoDBStatusHandler(client=src)
        else:  # pragma: no cover
            raise NotImplementedError("backend {} of type {}".format(src, type(src)))


class MongoDBStatusHandler():
    """Abstraction layer over MongoDB backend."""

    def __init__(self, db_uri=None, client=None, collection=None):
        """Initialize."""
        if db_uri:  # pragma: no cover
            logger.debug("connect to MongoDB: {}".format(db_uri))
            self._client = pymongo.MongoClient(db_uri, tz_aware=True)
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif client:
            logger.debug("use existing PyMongo client instance: {}".format(client))
            self._client = client
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif collection:
            self._client = None
            self._db = None
            self._jobs = collection
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
            state = query.get("state")
            # group states are lowercase!
            if state.lower() in job_states:
                # for all group states (todo, doing, done) query full group
                query.update(state={"$in": job_states[state.lower()]})
            # celery task states are uppercase!
            else:
                query.update(state={"$in": [state.upper()]})

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

        logger.debug("MongoDB query: {}".format(query))
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
            return None

    def update(self, job_id=None, metadata={}):
        """
        Update job entry in database.

        Parameters
        ----------
        job_id : str
            Unique job ID.
        metadata : dict
            Job metadata.

        Returns
        -------
        Updated entry
        """
        if job_id:
            logger.debug("got event metadata {}".format(metadata))
            entry = self._event_to_db_schema(job_id, metadata)
            logger.debug("upsert entry: {}".format(entry))
            return self._entry_to_geojson(
                self._jobs.find_one_and_update(
                    {"job_id": job_id},
                    {"$set": entry},
                    upsert=True,
                    return_document=pymongo.ReturnDocument.AFTER
                )
            )

    def new(self, job_id=None, metadata=None):
        """
        Create new job entry in database.

        Parameters
        ----------
        job_id : str
            Unique job ID.
        metadate : dict
            Job metadata.

        Returns
        -------
        None
        """
        logger.debug(f"got new job {job_id} with metadata {metadata}")
        entry = models.Job(
            job_id=job_id,
            state=models.State["pending"],
            geometry={},
            mapchete=metadata,

        )
        self._jobs.insert_one(entry.dict())
        return self._entry_to_geojson(entry.dict())

    def set(self, job_id, state=None, progress=None, exception=None):
        if job_id:
            entry = {"job_id": job_id}
            if state is not None:
                entry.update(state=state)
            if progress is not None:
                entry.update(progress=progress)
            if exception is not None:
                entry.update(exception=exception)
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
            "id": entry["job_id"],
            "geometry": entry["geometry"],
            "properties": {
                k: entry.get(k)
                for k in entry.keys()
                if k not in ["job_id", "geometry"]
            }
        }

    def _event_to_db_schema(self, job_id=None, metadata=None):
        """Map celery event metadata to entry schema."""
        # example metadata keys returned by celery:
        # metadata.keys():
        # ['args', 'type', 'clock', 'timestamp', 'kwargs', 'root_id', 'hostname',
        # 'local_received', 'uuid', 'routing_key', 'eta', 'name', 'exchange',
        # 'expires', 'retries', 'utcoffset', 'state', 'queue', 'parent_id', 'pid']
        # in 'kwargs' we have the process information encoded as json

        # json.loads(metadata["kwargs"]).keys():
        # ['command', 'queue', 'parent_job_id', 'child_job_id', 'process_area', 'mode',
        # 'bounds', 'tile', 'point', 'mapchete_config', 'wkt_geometry', 'zoom']

        # remember timestamp when process started
        if metadata.get("type") in ["task-started", "task-received"]:
            metadata.update(started=metadata.get("timestamp"))

        # get all celery related metadata
        entry = {
            "job_id": job_id,
            **{
                k: v for k, v in metadata.items()
                if k in MONGO_ENTRY_SCHEMA.keys() and v is not None
            }
        }

        # update state to TERMINATED if task was terminated successfully or was revoked
        if metadata.get("terminated"):
            entry.update(state="TERMINATED")

        return entry

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        pass
