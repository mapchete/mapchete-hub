import logging
import os
from typing import Optional
from uuid import uuid4

from datetime import datetime
from mapchete.enums import Status
from pydantic import NonNegativeInt
import pymongo
from shapely.geometry import box, mapping, shape

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.geometry import process_area_from_config
from mapchete_hub.models import MapcheteJob, JobEntry
from mapchete_hub.random_names import random_name
from mapchete_hub.settings import mhub_settings
from mapchete_hub.timetools import str_to_date

logger = logging.getLogger(__name__)


class MongoDBStatusHandler(BaseStatusHandler):
    """Abstraction layer over MongoDB backend."""

    def __init__(self, db_uri=None, client=None, database=None):
        """Initialize."""
        if db_uri:  # pragma: no cover
            logger.debug("connect to MongoDB: %s", db_uri)
            self._client = pymongo.MongoClient(db_uri, tz_aware=False)
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif client:  # pragma: no cover
            logger.debug("use existing PyMongo client instance: %s", client)
            self._client = client
            self._db = self._client["mhub"]
            self._jobs = self._db["jobs"]
        elif database:
            self._client = None
            self._db = database
            self._jobs = self._db["jobs"]
        logger.debug("active client %s", self._client)

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
        logger.debug("raw query: %s", query)

        # parsing job state groups and job states
        if query.get("state") is not None:
            states = query.get("state")
            states = states if isinstance(states, list) else [states]
            states = [Status[state] for state in states]
            # group states are lowercase!
            query.update(state={"$in": states})

        # convert bounds query into a geo search query
        if query.get("bounds") is not None:
            query.update(
                geometry={
                    "$geoIntersects": {"$geometry": mapping(box(*query.get("bounds")))}
                }
            )
            query.pop("bounds")

        # convert from_date and to_date kwargs to updated query
        if query.get("from_date") or query.get("to_date"):
            for i in ["from_date", "to_date"]:
                query[i] = (
                    str_to_date(query.get(i))
                    if isinstance(query.get(i), str)
                    else query.get(i)
                )
            query.update(
                updated={
                    k: v
                    for k, v in zip(
                        # don't know wy "$lte", "$gte" and not the other way round, but the test passes
                        # ["$lte", "$gte"],
                        ["$gte", "$lte"],
                        [query.get("from_date"), query.get("to_date")],
                    )
                    if v is not None
                }
            )
            query.pop("from_date", None)
            query.pop("to_date", None)

        logger.debug("MongoDB query: %s", query)
        jobs = []
        for entry in self._jobs.find(query):
            try:
                jobs.append(self._entry_to_geojson(entry))
            except Exception as exc:  # pragma: no cover
                logger.exception("cannot create GeoJSON from entry: %s", exc)
        return jobs

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
        else:  # pragma: no cover
            raise KeyError(f"job {job_id} not found in the database: {result}")

    def new(self, job_config: MapcheteJob):
        """
        Create new job entry in database.
        """
        job_id = uuid4().hex
        logger.debug(
            f"got new job with config {job_config} and assigning job ID {job_id}"
        )
        process_area = process_area_from_config(
            job_config, dst_crs=os.environ.get("MHUB_BACKEND_CRS", "EPSG:4326")
        )[0]
        started = datetime.utcnow()
        entry = JobEntry(
            job_id=job_id,
            url=os.path.join(mhub_settings.self_url, "jobs", job_id),
            state=None,
            geometry=process_area,
            bounds=shape(process_area).bounds,
            mapchete=job_config,
            output_path=job_config.dict()["config"]["output"]["path"],
            started=started,
            updated=started,
            job_name=job_config.params.get("job_name") or random_name(),
            dask_specs=job_config.params.get("dask_specs"),
        )
        result = self._jobs.insert_one(entry.dict())
        if result.acknowledged:
            return self.job(job_id)
        else:  # pragma: no cover
            raise RuntimeError(f"entry {entry} could not be inserted into MongoDB")

    def set(
        self,
        job_id: str,
        state: Optional[Status] = None,
        current_progress: Optional[NonNegativeInt] = None,
        total_progress: Optional[NonNegativeInt] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        dask_dashboard_link: Optional[str] = None,
        dask_specs: Optional[dict] = None,
        results: Optional[str] = None,
        **kwargs,
    ):
        entry = {"job_id": job_id}
        timestamp = datetime.utcnow()
        logger.debug("update timestamp: %s", timestamp)
        if state is not None:
            entry.update(state=Status[state])
            if state == "done":
                logger.debug(self.job(job_id)["properties"]["started"])
                entry.update(
                    runtime=(
                        timestamp - self.job(job_id)["properties"]["started"]
                    ).total_seconds(),
                    finished=timestamp,
                )
        attributes = dict(
            current_progress=current_progress,
            total_progress=total_progress,
            exception=exception if exception is None else str(exception),
            traceback=traceback,
            dask_dashboard_link=dask_dashboard_link,
            dask_specs=dask_specs,
            results=results,
            **kwargs,
        )
        entry.update(**{k: v for k, v in attributes.items() if v is not None})
        # add timestamp to entry
        entry.update(updated=timestamp)
        logger.debug("upsert entry: %s", entry)
        return self._entry_to_geojson(
            self._jobs.find_one_and_update(
                {"job_id": job_id},
                {"$set": entry},
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER,
            )
        )
