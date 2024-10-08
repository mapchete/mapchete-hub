from contextlib import contextmanager
from typing import Generator

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.job_handler.background_thread import BackgroundThreadJobHandler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.job_handler.k8s_worker import KubernetesWorkerJobHandler
from mapchete_hub.job_handler.mhub_worker import MHubWorkerJobHandler
from mapchete_hub.settings import MHubSettings, mhub_settings


@contextmanager
def init_job_handler(
    status_handler: BaseStatusHandler, mhub_settings: MHubSettings = mhub_settings
) -> Generator[JobHandlerBase, None, None]:
    if mhub_settings.job_handler == "background-thread":
        with BackgroundThreadJobHandler.from_settings(
            settings=mhub_settings, status_handler=status_handler
        ) as handler:
            yield handler
    elif mhub_settings.job_handler == "mhub-worker":
        with MHubWorkerJobHandler() as handler:
            yield handler
    elif mhub_settings.job_handler == "k8s-job-worker":
        with KubernetesWorkerJobHandler.from_settings(
            settings=mhub_settings, status_handler=status_handler
        ) as handler:
            yield handler
    else:
        raise KeyError(f"unknown job handler: {mhub_settings.job_handler}")
