import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, asynccontextmanager
from typing import Optional

from dask.distributed import LocalCluster

from mapchete_hub import __version__
from mapchete_hub.db import BaseStatusHandler, init_backenddb
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


class Resources:
    backend_db: BaseStatusHandler
    thread_pool: Optional[ThreadPoolExecutor] = None
    local_cluster: Optional[LocalCluster] = None

    def __setattr__(self, name, value):
        self.__dict__[name] = value


resources = Resources()


@asynccontextmanager
async def lifespan(*args):
    """
    Setup and tear down of additional resources required by mapchete Hub.
    """

    # mhub is online message
    try:
        if mhub_settings.slack_token:  # pragma: no cover
            from slack_sdk import WebClient

            client = WebClient(token=mhub_settings.slack_token)
            client.chat_postMessage(
                channel=mhub_settings.slack_channel,
                text=(
                    f":eox_eye: *{mhub_settings.self_instance_name} version {__version__} "
                    f"awaiting orders on* {mhub_settings.self_url}"
                ),
            )
    except ImportError:  # pragma: no cover
        pass

    # use context managers to assert proper shutdown when app exits
    with ExitStack() as exit_stack:
        # start status handler
        if mhub_settings.backend_db == "memory":
            logger.warning(
                "MHUB_MONGODB_URL not provided; using in-memory metadata store"
            )
        resources.backend_db = exit_stack.enter_context(
            init_backenddb(src=mhub_settings.backend_db)
        )

        # start thread pool
        resources.thread_pool = exit_stack.enter_context(
            ThreadPoolExecutor(max_workers=mhub_settings.max_parallel_jobs)
        )

        # start local dask cluster if required
        if (
            mhub_settings.dask_gateway_url is None
            and mhub_settings.dask_scheduler_url is None
        ):
            logger.debug("initializing LocalCluster")
            resources.local_cluster = exit_stack.enter_context(
                LocalCluster(processes=False, n_workers=4, threads_per_worker=8)
            )

        yield

        resources.thread_pool.shutdown()
