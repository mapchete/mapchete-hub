import logging
import os
from typing import Optional
from uuid import uuid4

from datetime import datetime
from mapchete.enums import Status
from pydantic import NonNegativeInt
from shapely import to_wkt
from shapely.geometry import box, shape

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.geometry import process_area_from_config
from mapchete_hub.models import MapcheteJob, JobEntry
from mapchete_hub.random_names import random_name
from mapchete_hub.settings import mhub_settings
from mapchete_hub.timetools import str_to_date

logger = logging.getLogger(__name__)


class MemoryStatusHandler(BaseStatusHandler):
    """Abstraction layer over in-memory backend."""

    def __init__(self, *args, **kwargs):
        self._jobs = {}

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
        return self._entry_to_geojson(self._jobs[job_id])

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

        bbox = box(*query.get("bounds")) if query.get("bounds") else None

        def _intersects_with(job, value, field="geometry"):
            return shape(job[field]).intersects(value)

        def _updated_since(job, value, field="updated"):
            return str_to_date(job[field]) >= value

        def _updated_until(job, value, field="updated"):
            return str_to_date(job[field]) <= value

        def _field_equals(job, value, field=None):
            return job[field] == value

        result = []
        for job in self._jobs.values():
            for field, value in query.items():
                # skip job if any query field does not match
                if field == "bounds":
                    if not _intersects_with(job, bbox):  # pragma: no cover
                        break
                elif field == "from_date":
                    if not _updated_since(job, value):
                        break
                elif field == "to_date":
                    if not _updated_until(job, value):
                        break
                elif field == "state":
                    states = value if isinstance(value, list) else [value]
                    states = [Status[state] for state in states]
                    if job[field] not in states:
                        break
                elif not _field_equals(job, value, field=field):
                    break
            else:
                try:
                    result.append(self._entry_to_geojson(job))
                except Exception as exc:  # pragma: no cover
                    logger.exception("cannot create GeoJSON from entry: %s", exc)
        return result

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
            area=to_wkt(shape(process_area)),
            mapchete=job_config,
            output_path=job_config.dict()["config"]["output"]["path"],
            started=started,
            updated=started,
            job_name=job_config.params.get("job_name") or random_name(),
            dask_specs=job_config.params.get("dask_specs"),
        )
        self._jobs[job_id] = entry.dict()
        return self.job(job_id)

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
        entry = self._jobs[job_id]
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
        self._jobs[job_id] = entry
        return self.job(job_id)
