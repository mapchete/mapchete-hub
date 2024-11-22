from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from dask.distributed import LocalCluster
from mapchete.commands.observer import Observers
from mapchete.enums import Status

from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.job_wrapper import job_wrapper
from mapchete_hub.models import JobEntry

logger = logging.getLogger(__name__)


class BackgroundThreadJobHandler(JobHandlerBase):
    _thread_pool: ThreadPoolExecutor
    local_cluster: Optional[LocalCluster] = None
    status_handler: BaseStatusHandler
    self_instance_name: str = ""
    max_parallel_jobs: int
    backend_db_event_rate_limit: float = 0.2
    dask_gateway_url: Optional[str] = None
    dask_scheduler_url: Optional[str] = None

    def __init__(
        self,
        status_handler: BaseStatusHandler,
        max_parallel_jobs: int = 3,
        self_instance_name: str = "",
        backend_db_event_rate_limit: float = 0.2,
        dask_gateway_url: Optional[str] = None,
        dask_scheduler_url: Optional[str] = None,
        **kwargs,
    ):
        self.status_handler = status_handler
        self.max_parallel_jobs = max_parallel_jobs
        self.self_instance_name = self_instance_name
        self.dask_gateway_url = dask_gateway_url
        self.dask_scheduler_url = dask_scheduler_url
        self.backend_db_event_rate_limit = backend_db_event_rate_limit

    def __enter__(self):
        """Enter context."""
        self._thread_pool = ThreadPoolExecutor(max_workers=self.max_parallel_jobs)
        # start local dask cluster if required
        if self.dask_gateway_url is None and self.dask_scheduler_url is None:
            logger.debug("initializing LocalCluster")
            self.local_cluster = LocalCluster(
                processes=False, n_workers=4, threads_per_worker=8
            )

        return self

    def __exit__(self, *args):
        """Exit context."""
        logger.debug("shutting down background thread pool ...")
        self._thread_pool.shutdown()
        if self.local_cluster:
            logger.debug("closing dask LocalCluster ...")
            self.local_cluster.close()

    def submit(
        self, job_entry: JobEntry, observers: Optional[Observers] = None
    ) -> JobEntry:
        observers = observers or self.get_job_observers(job_entry)
        try:
            # send task to background to be able to quickly return a message
            self._thread_pool.submit(
                job_wrapper,
                job_entry,
                observers=observers,
                local_cluster=self.local_cluster,
            )
            job_entry.status = Status.pending
            return job_entry
        except Exception as exc:
            observers.notify(status=Status.failed, exception=exc)
            raise

    @staticmethod
    def from_settings(
        settings, status_handler: BaseStatusHandler
    ) -> BackgroundThreadJobHandler:
        return BackgroundThreadJobHandler(
            status_handler=status_handler,
            max_parallel_jobs=settings.max_parallel_jobs,
            self_instance_name=settings.self_instance_name,
            backend_db_event_rate_limit=settings.backend_db_event_rate_limit,
            dask_gateway_url=settings.dask_gateway_url,
            dask_scheduler_url=settings.dask_scheduler_url,
        )
