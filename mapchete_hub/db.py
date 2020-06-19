from datetime import datetime
import logging
import mongomock.collection
import mongomock.database
import pymongo
from shapely.geometry import Polygon

from mapchete_hub.api import job_states

logger = logging.getLogger(__name__)


MONGO_ENTRY_SCHEMA = {
    "exception": str,
    "geometry": dict,
    "mapchete": {
        "command": str,
        "params": dict,
        "config": dict,
    },
    "job_id": str,
    "parent_job_id": str,
    "child_job_ids": list,
    "previous_job_id": str,
    "next_job_id": str,
    "hostname": str,
    "progress_data": dict,
    "runtime": float,
    "started": float,
    "state": str,
    "terminated": bool,
    "timestamp": float,
    "traceback": str,
    "output_path": str,
    "command": str,
    "queue": str,
    "job_name": str,
}

OUTPUT_SCHEMA = {
    "id": "job_id",
    "geometry": Polygon,
    "properties": {
        "mapchete": "mapchete"
    }
}


class BackendDB():
    """Class to communicate with backend database."""

    def __new__(self, src=None):
        """Initialize."""
        if isinstance(src, str) and src.startswith("mongodb"):  # pragma: no cover
            return MongoDBStatusHandler(db_uri=src)
        elif isinstance(src, (pymongo.MongoClient, mongomock.database.Database)):
            return MongoDBStatusHandler(client=src)
        elif isinstance(src, mongomock.collection.Collection):
            return MongoDBStatusHandler(collection=src)
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
        query = {
            k: v for k, v in kwargs.items() if v is not None
        }
        # enable job_states groups, e.g. "doing"
        if query.get("state") is not None:
            state = query.get("state")
            if state.lower() in job_states:
                query.update(state={"$in": job_states[state]})
        # convert bounds query into a geo search query
        if query.get("bounds") is not None:
            left, bottom, right, top = query.get("bounds")
            query.update(
                geometry={
                    "$geoIntersects": {"$box": [[bottom, left], [top, right]]}
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
        logger.debug("got new job {} with metadata {}".format(job_id, metadata))
        # metadata looks like:
        # job_id=job_id,
        # command=job["command"],
        # params=job["params"],
        # config=cleanup_datetime(job["config"]),
        # parent_job_id=parent_job_id,
        # child_job_id=child_job_id,
        # process_area=mapping(process_area),
        # process_area_process_crs=mapping(process_area_process_crs),
        entry = {
            "child_job_ids": metadata.get("child_job_id"),
            "geometry": metadata.get("process_area_process_crs"),
            "job_id": job_id,
            "mapchete": {
                "command": metadata.get("command"),
                "params": metadata.get("params"),
                "config": metadata.get("config"),
            },
            "next_job_id": metadata.get("next_job_id"),
            "parent_job_id": metadata.get("parent_job_id"),
            "previous_job_id": metadata.get("previous_job_id"),
            "state": "PENDING",
            "output_path": metadata.get("config", {}).get("output", {}).get("path"),
            "command": metadata.get("command"),
            "queue": metadata.get("params").get("queue"),
            "job_name": metadata.get("params").get("job_name"),
        }
        self._jobs.insert_one(entry)
        return self._entry_to_geojson(entry)

    def _entry_to_geojson(self, entry):
        return {
            "id": entry["job_id"],
            "geometry": entry["geometry"],
            "properties": {
                k: entry.get(k)
                for k in MONGO_ENTRY_SCHEMA.keys()
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
