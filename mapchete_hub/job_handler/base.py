from abc import ABC, abstractmethod
from mapchete.commands.observer import Observers

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.models import JobEntry
from mapchete_hub.observers.db_updater import DBUpdater
from mapchete_hub.observers.slack_messenger import SlackMessenger


class JobHandlerBase(ABC):
    self_instance_name: str
    status_handler: BaseStatusHandler
    backend_db_event_rate_limit: float

    def get_job_observers(self, job_entry: JobEntry) -> Observers:
        db_updater = DBUpdater(
            backend_db=self.status_handler,
            job_entry=job_entry,
            event_rate_limit=self.backend_db_event_rate_limit,
        )
        # initialize slack messenger
        slack_messenger = SlackMessenger(self.self_instance_name, job_entry)
        # once the initialization message is sent, we remember the thread ID
        # and channel ID for all follow-up messages, even if the job thread dies
        db_updater.set(
            slack_thread_ds=slack_messenger.thread_ts,
            slack_channel_id=slack_messenger.channel_id,
        )
        return Observers([db_updater, slack_messenger])

    @abstractmethod
    def submit(self, job_entry: JobEntry) -> None:
        """Submit a job."""

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        return
