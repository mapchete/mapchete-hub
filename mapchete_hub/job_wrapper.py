from functools import partial
import logging
import time

from mapchete.commands import execute
from mapchete.commands.observer import Observers
from mapchete.enums import Status
from mapchete.errors import JobCancelledError
from mapchete.path import MPath

from mapchete_hub import __version__
from mapchete_hub.cluster import get_dask_executor
from mapchete_hub.models import MapcheteJob, JobEntry
from mapchete_hub.db import BaseStatusHandler
from mapchete_hub.observers import DBUpdater, SlackMessenger
from mapchete_hub.settings import mhub_settings


logger = logging.getLogger(__name__)


def job_wrapper(
    job: JobEntry,
    job_config: MapcheteJob = None,
    backend_db: BaseStatusHandler = None,
    dask_cluster_setup: dict = None,
):
    # prepare observers for job:
    db_updater = DBUpdater(
        backend_db=backend_db,
        job_id=job.job_id,
        event_rate_limit=mhub_settings.backend_db_event_rate_limit,
    )
    slack_messenger = SlackMessenger(
        mhub_settings.self_instance_name, job.url, job.job_name
    )
    observers = Observers([db_updater, slack_messenger])
    try:
        logger.info("start fastAPI background task with job %s", job.job_id)

        mapchete_config = job_config.config

        # TODO: this needs to be fixed in the core package
        if mapchete_config.process_parameters is None:
            mapchete_config.process_parameters = {}

        # relative output paths are not useful, so raise exception
        out_path = MPath.from_inp(dict(mapchete_config.output))
        if not out_path.is_absolute():  # pragma: no cover
            raise ValueError(f"process output path must be absolute: {out_path}")

        # if there are too many jobs in parallel, wait
        while (
            # TODO: verify job states can be compared
            len(
                backend_db.jobs(
                    state=[
                        Status.parsing,
                        Status.initializing,
                        Status.running,
                        Status.retrying,
                    ]
                )
            )
            >= mhub_settings.max_parallel_jobs
        ):
            time.sleep(mhub_settings.max_parallel_jobs_interval_seconds)

        execute(
            mapchete_config.model_dump(),
            retries=mhub_settings.cancellederror_tries,
            executor_getter=partial(
                get_dask_executor, job.job_id, job_config.params.get("dask_specs")
            ),
            observers=[db_updater, slack_messenger],
            cancel_on_exception=JobCancelledError,
            **{
                k: v
                for k, v in job_config.params.items()
                if k not in ["job_name", "dask_specs"]
            },
        )

        # NOTE: this is not ideal, as we have to get the STACTA path from the output
        db_updater.set(
            result={
                "imagesOutput": {
                    "href": mapchete_config.output["path"],
                    "type": "application/json",
                }
            },
        )
    except JobCancelledError:
        pass
    except Exception as exc:
        observers.notify(status=Status.failed, exception=exc)
        logger.exception(exc)
    finally:
        logger.info("end fastAPI background task with job %s", job.job_id)
