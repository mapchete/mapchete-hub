import logging
import time
import traceback
from typing import Optional

from mapchete.enums import Status
from mapchete.commands.observer import ObserverProtocol
from mapchete.pretty import pretty_seconds
from mapchete.types import Progress

from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.slack import send_slack_message


logger = logging.getLogger(__name__)


class DBUpdater(ObserverProtocol):
    last_event: float = 0.0
    event_rate_limit: float = 0.2
    backend_db: BaseStatusHandler

    def __init__(
        self, backend_db: BaseStatusHandler, job_id: str, event_rate_limit: float = 0.2
    ):
        self.backend_db = backend_db
        self.job_id = job_id
        self.event_rate_limit = event_rate_limit

    def update(
        self,
        *args,
        status: Optional[Status] = None,
        progress: Optional[Progress] = None,
        **kwargs,
    ):
        set_kwargs = dict()
        # job status always has to be updated
        if status:
            set_kwargs.update(status=status)
            logger.debug("DB update: job %s status changed to %s", self.job_id, status)

        if progress:
            # progress only at given minimal intervals
            event_time_passed = time.time() - self.last_event
            if (
                event_time_passed > self.event_rate_limit
                or progress.current == progress.total
            ):
                logger.debug(
                    "DB update: job %s progress changed to %s/%s",
                    progress.current,
                    progress.total,
                )
                set_kwargs.update(progress=progress)
                self.last_event = time.time()

        if set_kwargs:
            self.backend_db.set(self.job_id, **set_kwargs)


class SlackMessenger(ObserverProtocol):
    self_instance_name: str
    job_url: str
    job_name: str
    started: int

    def __init__(
        self,
        self_instance_name: str,
        job_url: str,
        job_name: str,
    ):
        self.self_instance_name = self_instance_name
        self.job_url = job_url
        self.job_name = job_name
        self.message_prefix = (
            f"{self.self_instance_name}: <{self.job_url}|{self.job_name}>"
        )
        self.started = time.time()

    def update(
        self,
        *args,
        status: Optional[Status] = None,
        exception: Optional[Exception] = None,
        **kwargs,
    ):
        if status:
            send_slack_message(f"*{self.message_prefix} {status.value}*")
        if exception:
            send_slack_message(
                f"*{self.job_name} failed after{pretty_seconds(time.time() - self.started)}*\n"
                f"{exception}\n"
                f"{''.join(traceback.format_tb(exception.__traceback__))}"
            )
