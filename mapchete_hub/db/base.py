"""
Abstraction classes for database.
"""

from abc import ABC, abstractmethod
import logging
import os
from typing import Optional

from mapchete.enums import Status
from pydantic import NonNegativeInt
from shapely.geometry import shape

from mapchete_hub.models import MapcheteJob

logger = logging.getLogger(__name__)

MHUB_SELF_URL = os.environ.get("MHUB_SELF_URL", "/")


class BaseStatusHandler(ABC):
    """Base functions for status handler."""

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def new(self, job_config: MapcheteJob):
        """
        Create new job entry in database.
        """

    @abstractmethod
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
        """
        Set job metadata.
        """

    def _entry_to_geojson(self, entry: dict) -> dict:
        return {
            "type": "Feature",
            "id": str(entry["job_id"]),
            "geometry": entry["geometry"],
            "bounds": entry.get("bounds", shape(entry["geometry"]).bounds),
            "properties": {
                k: entry.get(k)
                for k in entry.keys()
                if k not in ["job_id", "geometry", "id", "_id", "bounds"]
            },
        }

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        return
