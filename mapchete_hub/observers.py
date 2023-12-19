import logging
import time
import traceback
from typing import Optional

from mapchete.commands.observer import ObserverProtocol
from mapchete.errors import JobCancelledError
from mapchete.executor import DaskExecutor
from mapchete.pretty import pretty_seconds
from mapchete.types import Progress

from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.enums import Status
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
        executor: Optional[DaskExecutor] = None,
        exception: Optional[Exception] = None,
        **kwargs,
    ):
        set_kwargs = dict()

        # check always if job was cancelled but respect the rate limit
        event_time_passed = time.time() - self.last_event
        if event_time_passed > self.event_rate_limit:
            current_status = self.backend_db.job(self.job_id).status
            # if job status was set to cancelled, raise a JobCancelledError
            if current_status == Status.cancelled:
                raise JobCancelledError("job was cancelled")

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
                    self.job_id,
                    progress.current,
                    progress.total,
                )
                set_kwargs.update(progress=progress)
                self.last_event = time.time()

        if executor:
            set_kwargs.update(dask_dashboard_link=executor._executor.dashboard_link)

        if exception:
            set_kwargs.update(
                exception=exception,
                traceback="\n".join(traceback.format_tb(exception.__traceback__)),
            )

        if set_kwargs:
            self.set(**set_kwargs)

    def set(self, **kwargs):
        if kwargs:
            self.backend_db.set(self.job_id, **kwargs)


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
        executor: Optional[DaskExecutor] = None,
        exception: Optional[Exception] = None,
        **kwargs,
    ):
        if status:
            if status in [Status.done, Status.failed, Status.cancelled]:
                send_slack_message(
                    f"*{self.message_prefix} {status.value} after {pretty_seconds(time.time() - self.started)}*"
                )
            else:
                send_slack_message(f"*{self.message_prefix} {status.value}*")
        if exception:
            send_slack_message(
                f"{exception}\n"
                f"{''.join(traceback.format_tb(exception.__traceback__))}"
            )
        if executor:
            send_slack_message(
                f"*{self.message_prefix}*: <{executor._executor.dashboard_link}|cluster dashboard online>"
            )
