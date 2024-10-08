import logging
from contextlib import asynccontextmanager

from mapchete_hub import __version__
from mapchete_hub.db import BaseStatusHandler, init_backenddb
from mapchete_hub.job_handler import init_job_handler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


class Resources:
    backend_db: BaseStatusHandler
    job_handler: JobHandlerBase

    def __setattr__(self, name, value):
        self.__dict__[name] = value


resources = Resources()


@asynccontextmanager
async def setup_lifespan_resources(*args):
    """
    Setup and tear down of additional resources required by mapchete Hub.
    """
    # mhub is online message
    try:
        if mhub_settings.slack_token:  # pragma: no cover
            from slack_sdk import WebClient

            client = WebClient(token=mhub_settings.slack_token)
            if mhub_settings.slack_channel:
                client.chat_postMessage(
                    channel=mhub_settings.slack_channel,
                    text=(
                        f":eox_eye: *{mhub_settings.self_instance_name} version {__version__} "
                        f"awaiting orders on* {mhub_settings.self_url}"
                    ),
                )
            else:
                raise ValueError("slack_channel name has to be provided")
    except ImportError:  # pragma: no cover
        pass

    if mhub_settings.backend_db == "memory":
        logger.warning("MHUB_BACKEND_DB not provided; using in-memory metadata store")
    # use context managers to assert proper shutdown when app exits
    # start status handler
    with init_backenddb(src=mhub_settings.backend_db) as backend_db:
        resources.backend_db = backend_db
        # start thread pool
        with init_job_handler(
            status_handler=resources.backend_db, mhub_settings=mhub_settings
        ) as job_handler:
            resources.job_handler = job_handler

            yield
