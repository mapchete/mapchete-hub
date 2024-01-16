import logging
import time
import traceback
from typing import Any, Optional

from mapchete.commands.observer import ObserverProtocol
from mapchete.enums import Status
from mapchete.errors import JobCancelledError
from mapchete.executor import DaskExecutor
from mapchete.pretty import pretty_seconds
from mapchete.types import Progress

from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.settings import mhub_settings

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
        if event_time_passed > self.event_rate_limit and status not in [
            Status.failed,
            Status.cancelled,
        ]:
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
                exception=repr(exception),
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
    submitted: float
    started: float
    thread_ts: Optional[str] = None
    client: Optional[Any] = None

    def __init__(
        self,
        self_instance_name: str,
        job_url: Optional[str] = None,
        job_name: Optional[str] = None,
    ):
        self.self_instance_name = self_instance_name
        try:
            if mhub_settings.slack_token:  # pragma: no cover
                from slack_sdk import WebClient

                self.client = WebClient(token=mhub_settings.slack_token)
            else:  # pragma: no cover
                logger.debug("no MHUB_SLACK_TOKEN env variable set.")
        except ImportError:  # pragma: no cover
            logger.debug(
                "install 'slack' extra and set MHUB_SLACK_TOKEN to send messages to slack"
            )

        self.job_url = job_url
        self.job_name = job_name
        self.submitted = time.time()
        self.started = self.submitted
        self.retries = 0

    def update(
        self,
        *_,
        status: Optional[Status] = None,
        executor: Optional[DaskExecutor] = None,
        exception: Optional[Exception] = None,
        message: Optional[str] = None,
        **__,
    ):
        if status:
            # count job runtime from initialization on
            if status == Status.initializing:
                self.started = time.time()

            if status == Status.failed and isinstance(exception, JobCancelledError):
                pass

            # in final statuses, report runtime
            elif status in [Status.done, Status.failed, Status.cancelled]:
                retry_text = (
                    "1 retry" if self.retries == 1 else f"{self.retries} retries"
                )
                self.send(
                    f"*{status.value} after "
                    f"{pretty_seconds(time.time() - self.started)} and {retry_text}*"
                )
                if exception:
                    self.send(
                        f"{repr(exception)}\n"
                        f"{''.join(traceback.format_tb(exception.__traceback__))}"
                    )

            elif status == Status.retrying:
                self.retries += 1
                if message:
                    self.send(f"*{status.value}*: {message}")
            elif status == Status.running:
                self.send(f"*{status.value} ...*")

        if executor:
            self.send(f"<{executor._executor.dashboard_link}|cluster dashboard online>")

    def send(self, message: str, thread_ts: Optional[str] = None) -> None:
        thread_ts = thread_ts or self.thread_ts
        if self.client:
            logger.debug("announce on slack, (thread: %s): %s", thread_ts, message)
            response = self.client.chat_postMessage(
                channel=mhub_settings.slack_channel, text=message, thread_ts=thread_ts
            )

            if not response.get("ok"):
                logger.debug("slack message not sent: %s", response.body)
            elif thread_ts is None:
                self.thread_ts = response.data.get("ts")
