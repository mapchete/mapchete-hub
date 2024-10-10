import logging
import time
import traceback
from enum import Enum
from typing import Any, Optional

from mapchete.commands.observer import ObserverProtocol
from mapchete.enums import Status
from mapchete.errors import JobCancelledError
from mapchete.executor import DaskExecutor
from mapchete.pretty import pretty_seconds

from mapchete_hub.models import JobEntry
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


class StatusEmojis(Enum):
    pending = ":large_blue_circle:"
    parsing = ":large_blue_circle:"
    initializing = ":large_blue_circle:"
    running = ":large_yellow_circle:"
    retrying = ":large_yellow_circle:"
    post_processing = ":large_yellow_circle:"
    done = ":large_green_circle:"
    cancelled = ":large_purple_circle:"
    failed = ":red_circle:"


def status_emoji(status: Status) -> str:
    return StatusEmojis[status.name].value


class SlackMessenger(ObserverProtocol):
    self_instance_name: str
    job: JobEntry
    submitted: float
    started: float
    thread_ts: Optional[str] = None
    channel_id: Optional[str] = None
    client: Optional[Any] = None

    def __init__(
        self,
        self_instance_name: str,
        job: JobEntry,
    ):
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
        self.self_instance_name = self_instance_name
        self.job = job
        self.thread_ts = job.slack_thread_ds
        self.channel_id = job.slack_channel_id
        self.submitted = time.time()
        self.started = self.submitted
        self.retries = 0
        self.job_message = (
            "{status_emoji} "
            + f"{mhub_settings.self_instance_name}: job *{self.job.job_name} "
            + "{status}*"
        )
        if self.thread_ts is None and self.channel_id is None:
            # send init message
            self.send(
                message=self.job_message.format(
                    status_emoji=status_emoji(Status.pending),
                    status=Status.pending.value,
                )
            )

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
            if status == Status.pending and message:
                self.send(message)
            # remember job runtime from initialization on
            if status == Status.initializing:
                self.started = time.time()

            # remember retries
            if status == Status.retrying:
                self.retries += 1
                if message:
                    self.send(f"{status.value}: {message}")

            # in final statuses, report runtime
            elif status in [Status.done, Status.failed, Status.cancelled]:
                retry_text = (
                    "1 retry" if self.retries == 1 else f"{self.retries} retries"
                )
                self.send(f"status changed to '{status.value}'")
                self.update_message(
                    message=self.job_message.format(
                        status_emoji=status_emoji(status), status=status.value
                    )
                    + f" after {pretty_seconds(time.time() - self.started)} using {retry_text}"
                )

            elif status == Status.running:
                self.send(f"status changed to '{status.value}'")
                self.update_message(
                    message=self.job_message.format(
                        status_emoji=status_emoji(status), status=status.value
                    )
                )

        if exception and not isinstance(exception, JobCancelledError):
            self.send(
                f"```\n"
                f"{repr(exception)}\n"
                f"{''.join(traceback.format_tb(exception.__traceback__))}"
                f"\n```"
            )

        if executor:
            self.send(
                f"dask scheduler online (see <{executor._executor.dashboard_link}|dashboard>)"
            )

    def _send_init_message(self):
        # send first message which can be updated by subsequent ones
        self._send(
            message=self.job_message.format(
                status_emoji=status_emoji(Status.pending),
                status=Status.pending.value,
            )
        )

    def _send(self, message: str):
        if self.client:  # pragma: no cover
            try:
                logger.debug(
                    "announce on slack, (thread: %s): %s", self.thread_ts, message
                )
                from slack_sdk.errors import SlackApiError

                response = self.client.chat_postMessage(
                    channel=mhub_settings.slack_channel,
                    text=message,
                    thread_ts=self.thread_ts,
                )
                if not response.get("ok"):
                    logger.debug("slack message not sent: %s", response.body)
                elif self.thread_ts is None and self.channel_id is None:
                    self.thread_ts = response.data.get("ts")
                    self.channel_id = response.data.get("channel")
            except SlackApiError as e:
                logger.exception(e)
                return

    def send(
        self,
        message: str,
    ) -> None:
        # special case if initialization message didn't get through:
        if self.thread_ts is None and self.channel_id is None:
            self._send_init_message()

        self._send(message)

    def update_message(self, message: str):
        if self.client:  # pragma: no cover
            if self.channel_id and self.thread_ts:
                self.client.chat_update(
                    text=message,
                    ts=self.thread_ts,
                    channel=self.channel_id,
                )
            else:
                self.send(message)
