import logging
import time
import traceback
from enum import Enum
from typing import Any, List, Optional

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
    slack_max_text_length: int = 4000

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
            traceback_text = (
                f"{repr(exception)}\n"
                f"{''.join(traceback.format_tb(exception.__traceback__))}"
            )
            self.send(traceback_text, prefix="```\n", postfix="\n```")

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

    def _send(self, message: str, prefix: str = "", postfix: str = ""):
        if self.client:  # pragma: no cover
            # send message in chunks if necessary
            for chunk in split_long_text(
                message,
                max_length=self.slack_max_text_length - len(prefix) - len(postfix),
            ):
                text = prefix + chunk + postfix
                try:
                    logger.debug(
                        "announce on slack, (thread: %s): %s", self.thread_ts, text
                    )
                    from slack_sdk.errors import SlackApiError

                    response = self.client.chat_postMessage(
                        channel=mhub_settings.slack_channel,
                        text=text,
                        thread_ts=self.thread_ts,
                    )
                    if not response.get("ok"):
                        logger.debug("slack message not sent: %s", response.body)
                    elif self.thread_ts is None and self.channel_id is None:
                        self.thread_ts = response.data.get("ts")
                        self.channel_id = response.data.get("channel")
                except SlackApiError as e:
                    logger.exception(e)

    def send(self, message: str, prefix: str = "", postfix: str = "") -> None:
        # special case if initialization message didn't get through:
        if self.thread_ts is None and self.channel_id is None:
            self._send_init_message()

        self._send(message, prefix=prefix, postfix=postfix)

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


def split_long_text(text: str, max_length: int = 4000) -> List[str]:
    out_chunks = []
    for line_chunk in chunk_by_newlines(text, max_length):
        if len(line_chunk) > max_length:
            for space_chunk in chunk_by_spaces(line_chunk, max_length):
                if len(space_chunk) > max_length:
                    for length_chunk in chunk_by_length(space_chunk, max_length):
                        out_chunks.append(length_chunk)
                else:
                    out_chunks.append(space_chunk)
        else:
            out_chunks.append(line_chunk)
    return out_chunks


def chunk_by_newlines(text: str, max_length: int = 150) -> List[str]:
    return _split(text, max_length, split_by="\n")


def chunk_by_spaces(text: str, max_length: int = 150) -> List[str]:
    return _split(text, max_length, split_by=" ")


def chunk_by_length(text: str, max_length: int = 150) -> List[str]:
    return [
        text[0 + chunk : max_length + chunk]
        for chunk in range(0, len(text), max_length)
    ]


def _split(text: str, max_length: int = 150, split_by: str = "\n") -> List[str]:
    out_chunks = []
    chunk = ""
    for element in text.split(split_by):
        element += split_by

        # let chunk grow as large as possible
        if len(chunk) + len(element) <= max_length:
            chunk += element

        # if single element is longer than maximum, just append it and reset chunk
        elif len(element) > max_length:
            out_chunks.append(chunk)
            out_chunks.append(element)
            chunk = ""

        # if adding then next element will exceed the max length, dump chunk now
        elif len(chunk) + len(element) > max_length:
            out_chunks.append(chunk)
            chunk = element

    out_chunks.append(chunk)

    return out_chunks
