import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pymongo
from mapchete.enums import Status
from mapchete.types import Progress
from shapely.geometry import box, mapping, shape

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.geometry import process_area_from_config
from mapchete_hub.models import JobEntry, MapcheteJob, to_status_list
from mapchete_hub.random_names import random_name
from mapchete_hub.settings import mhub_settings
from mapchete_hub.timetools import parse_to_date

logger = logging.getLogger(__name__)


class MongoDBStatusHandler(BaseStatusHandler):
    """Abstraction layer over MongoDB backend."""

    def __init__(self, db_uri=None, client=None, database=None):
        """Initialize."""
        if db_uri:  # pragma: no cover
            logger.debug("connect to MongoDB: %s", db_uri)
            self._client = pymongo.MongoClient(db_uri, tz_aware=False)
            self._db = self._client["mhub"]

        elif client:  # pragma: no cover
            logger.debug("use existing PyMongo client instance: %s", client)
            self._client = client
            self._db = self._client["mhub"]

        elif database:
            self._client = None
            self._db = database

        self._jobs = self._db["jobs"]

        logger.debug("active client %s", self._client)

    def __enter__(self):
        logger.debug("enter MongoDBStatusHandler")
        return self

    def __exit__(self, *args, **kwargs):
        logger.debug("exit MongoDBStatusHandler")
        if self._client:
            self._client.close()

    def jobs(self, **kwargs) -> List[JobEntry]:
        query = {k: v for k, v in kwargs.items() if v is not None}
        logger.debug("raw query: %s", query)

        # parsing job status groups
        status = query.get("status")
        if status is not None:
            status_list = to_status_list(status)
            # group statuses are lowercase!
            query.update(status={"$in": status_list})

        # convert bounds query into a geo search query
        bounds = query.get("bounds")
        if bounds is not None:
            query.update(
                geometry={"$geoIntersects": {"$geometry": mapping(box(*bounds))}}
            )
            query.pop("bounds")

        # convert from_date and to_date kwargs to updated query
        if query.get("from_date") or query.get("to_date"):
            for i in ["from_date", "to_date"]:
                date = query.get(i)
                if date:
                    query[i] = parse_to_date(date)
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
                jobs.append(JobEntry.from_dict(entry))
            except Exception as exc:  # pragma: no cover
                logger.exception("cannot create JobEntry from entry: %s", exc)
        return jobs

    def job(self, job_id) -> JobEntry:
        with pymongo.timeout(mhub_settings.mongodb_timeout):
            result = self._jobs.find_one({"job_id": job_id})
        if result:
            return JobEntry.from_dict(result)
        else:  # pragma: no cover
            raise KeyError(f"job {job_id} not found in the database: {result}")

    def new(self, job_config: MapcheteJob) -> JobEntry:
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
        submitted = datetime.now(timezone.utc)
        entry = JobEntry.from_dict(
            dict(
                job_id=job_id,
                url=os.path.join(mhub_settings.self_url, "jobs", job_id),
                status=Status.pending,
                geometry=process_area,
                bounds=list(shape(process_area).bounds),
                mapchete=job_config,
                output_path=job_config.config.output["path"],
                submitted=submitted,
                started=submitted,
                updated=submitted,
                job_name=job_config.params.get("job_name") or random_name(),
                dask_specs=job_config.params.get("dask_specs", dict()),
            )
        )
        with pymongo.timeout(mhub_settings.mongodb_timeout):
            result = self._jobs.insert_one(entry.model_dump())
        if result.acknowledged:
            return self.job(job_id)
        else:  # pragma: no cover
            raise RuntimeError(f"entry {entry} could not be inserted into MongoDB")

    def set(
        self,
        job_id: str,
        status: Optional[Status] = None,
        progress: Optional[Progress] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        dask_dashboard_link: Optional[str] = None,
        dask_specs: Optional[dict] = None,
        results: Optional[str] = None,
        **kwargs,
    ) -> JobEntry:
        entry: Dict[str, Any] = {"job_id": job_id}
        new_attributes: Dict[str, Any] = {
            k: v
            for k, v in dict(
                exception=exception if exception is None else str(exception),
                traceback=traceback,
                dask_dashboard_link=dask_dashboard_link,
                dask_specs=dask_specs,
                results=results,
                **kwargs,
            ).items()
            if v is not None
        }
        timestamp = datetime.now(timezone.utc)
        if status:
            new_attributes.update(status=Status[status])
            if status == Status.initializing:
                new_attributes.update(started=timestamp)
            elif status == Status.done:
                started = self.job(job_id).started
                if started:
                    new_attributes.update(
                        runtime=(timestamp - started).total_seconds(),
                        finished=timestamp,
                    )
        if progress:
            new_attributes.update(current_progress=progress.current)
            if progress.total is not None:
                new_attributes.update(total_progress=progress.total)
        logger.debug("%s: update attributes: %s", job_id, new_attributes)
        entry.update(**new_attributes)
        # add timestamp to entry
        entry.update(updated=timestamp)

        with pymongo.timeout(mhub_settings.mongodb_timeout):
            return JobEntry.from_dict(
                self._jobs.find_one_and_update(
                    {"job_id": job_id},
                    {"$set": entry},
                    upsert=True,
                    return_document=pymongo.ReturnDocument.AFTER,
                )
            )
