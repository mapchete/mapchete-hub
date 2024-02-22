import logging
from functools import partial
from typing import Optional

from mapchete.commands import execute
from mapchete.commands.observer import Observers
from mapchete.enums import Status
from mapchete.errors import JobCancelledError
from mapchete.path import MPath

from mapchete_hub import __version__
from mapchete_hub.cluster import get_dask_executor
from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.models import JobEntry, MapcheteJob
from mapchete_hub.observers import DBUpdater, SlackMessenger
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


def job_wrapper(
    job: JobEntry,
    job_config: MapcheteJob,
    observers: Optional[Observers] = Observers([]),
):
    logger.info("running job wrapper with job %s in background", job.job_id)

    mapchete_config = job_config.config

    # handle observers and job states while job is not being executed
    try:
        # relative output paths are not useful, so raise exception
        out_path = MPath.from_inp(dict(mapchete_config.output))
        if not out_path.is_absolute():  # pragma: no cover
            raise ValueError(f"process output path must be absolute: {out_path}")
    except Exception as exc:  # pragma: no cover
        logger.exception(exc)
        observers.notify(status=Status.failed, exception=exc)
        raise

    # observers and job states are handled by execute() from now on
    try:
        execute(
            mapchete_config.model_dump(),
            retries=mhub_settings.cancellederror_tries,
            executor_getter=partial(
                get_dask_executor,
                job_id=job.job_id,
                dask_specs=job_config.params.get("dask_specs"),
                dask_settings=job_config.params.get("dask_settings"),
            ),
            observers=observers.observers,
            cancel_on_exception=JobCancelledError,
            **{
                k: v
                for k, v in job_config.params.items()
                if k not in ["job_name", "dask_specs"]
            },
        )

        # NOTE: this is not ideal, as we have to get the STACTA path from the output
        observers.notify(
            result={
                "imagesOutput": {
                    "href": mapchete_config.output["path"],
                    "type": "application/json",
                }
            },
        )
    except JobCancelledError:
        logger.info("%s got cancelled.", job.job_id)
        observers.notify(status=Status.cancelled)
    except Exception as exc:
        logger.exception(exc)
    finally:
        logger.info("%s background task finished", job.job_id)
