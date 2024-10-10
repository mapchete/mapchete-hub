from __future__ import annotations
import logging

from mapchete.enums import Status

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.models import JobEntry
from mapchete_hub.settings import MHubSettings


logger = logging.getLogger(__name__)


class MHubWorkerJobHandler(JobHandlerBase):
    status_handler: BaseStatusHandler

    def __init__(
        self,
        status_handler: BaseStatusHandler,
        **kwargs,
    ):
        self.status_handler = status_handler

    def submit(self, job_entry: JobEntry) -> None:
        """Submit a job."""
        logger.debug(
            "job %s submitted and will have to be processed separately by a worker"
            % job_entry.job_id
        )
        # this step is important to send the initialization message to slack:
        observers = self.get_job_observers(job_entry)
        observers.notify(
            message="job waiting in queue to be picked up by manager",
            status=Status.pending,
        )

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        return

    @staticmethod
    def from_settings(
        settings: MHubSettings, status_handler: BaseStatusHandler
    ) -> MHubWorkerJobHandler:
        return MHubWorkerJobHandler(
            status_handler=status_handler,
        )
