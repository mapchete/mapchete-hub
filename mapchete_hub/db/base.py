"""
Abstraction classes for database.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from mapchete.enums import Status
from mapchete.types import Progress
from pydantic import NonNegativeInt

from mapchete_hub.models import JobEntry, MapcheteJob

logger = logging.getLogger(__name__)


class BaseStatusHandler(ABC):
    """Base functions for status handler."""

    @abstractmethod
    def jobs(self, **kwargs) -> List[JobEntry]:
        """
        Return jobs as list of GeoJSON features.

        Parameters
        ----------
        output_path : str
            Filter by output path.
        status : str
            Filter by job status.
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
    def job(self, job_id) -> JobEntry:
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
    def new(self, job_config: MapcheteJob) -> JobEntry:
        """
        Create new job entry in database.
        """

    @abstractmethod
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
        """
        Set job metadata.
        """

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        return
