import logging
import time
from typing import List

import click
from mapchete.enums import Status

from mapchete_hub import __version__
from mapchete_hub._log import setup_logger, LogLevels
from mapchete_hub.db import init_backenddb
from mapchete_hub.job_handler import KubernetesWorkerJobHandler
from mapchete_hub.models import JobEntry
from mapchete_hub.settings import mhub_settings
from mapchete_hub.timetools import (
    date_to_str,
    interval_to_timedelta,
    passed_time_to_timestamp,
)

logger = logging.getLogger(__name__)


@click.command()
@click.version_option(version=__version__, message="%(version)s")
@click.option(
    "--since",
    type=click.STRING,
    default="7d",
    help="Maximum age of jobs considered in the database.",
    show_default=True,
)
@click.option(
    "--inactive-since",
    type=click.STRING,
    default="5h",
    help="Time since jobs have been inactive.",
    show_default=True,
)
@click.option(
    "--pending-since",
    type=click.STRING,
    default="3d",
    help="Time since jobs have been pending.",
    show_default=True,
)
@click.option("--watch", is_flag=True, show_default=True)
@click.option(
    "--watch-interval", "-i", type=click.STRING, default="3s", show_default=True
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "notset"],
        case_sensitive=False,
    ),
    default="error",
    help="Set log level.",
)
@click.option(
    "--add-mapchete-logger",
    is_flag=True,
    help="Adds mapchete loggers.",
)
def main(
    since: str = "7d",
    inactive_since: str = "5h",
    pending_since: str = "3d",
    check_inactive_dashboard: bool = True,
    watch: bool = False,
    watch_interval: str = "3s",
    log_level: LogLevels = "info",
    add_mapchete_logger: bool = False,
):
    setup_logger(log_level, add_mapchete_logger=add_mapchete_logger)

    try:
        if mhub_settings.backend_db == "memory":
            raise ValueError("this command does not work with an in-memory db!")

        logger.debug("connecting to backend DB ...")
        with init_backenddb(mhub_settings.backend_db) as status_handler:
            logger.debug("creating KubernetesWorkerJobHandler ...")
            with KubernetesWorkerJobHandler.from_settings(
                status_handler=status_handler, settings=mhub_settings
            ) as job_handler:
                while True:
                    # get all jobs from given time range at once to avoid unnecessary requests to DB
                    all_jobs = status_handler.jobs(
                        from_date=date_to_str(passed_time_to_timestamp(since))
                    )
                    # determine jobs
                    currently_running_count = len(running_jobs(all_jobs))
                    logger.debug("currently %s jobs running", currently_running_count)
                    currently_queued = queued_jobs(jobs=all_jobs)
                    logger.debug("currently %s jobs queued", len(currently_queued))

                    # iterate to queued jobs and try to submit them
                    for job in currently_queued:
                        logger.info(
                            f"{currently_running_count}/{mhub_settings.max_parallel_jobs} jobs currently runnning"
                        )
                        if currently_running_count < mhub_settings.max_parallel_jobs:
                            logger.info("submitting job %s to cluster", job.job_id)
                            job_handler.submit(job)
                            currently_running_count += 1
                        else:
                            logger.info("maximum limit of running jobs reached")
                            break

                    # if --watch is activated, repeat until infinity
                    if watch:
                        logger.info("next check in %s", watch_interval)
                        time.sleep(interval_to_timedelta(watch_interval).seconds)
                    else:
                        break
    except Exception as exc:
        logger.exception(exc)
        raise


def queued_jobs(jobs: List[JobEntry]) -> List[JobEntry]:
    """Get jobs who are in pending state and not yet sent to kubernetes."""
    return [
        job for job in jobs if job.status == Status.pending and not job.submitted_to_k8s
    ]


def running_jobs(jobs: List[JobEntry]) -> List[JobEntry]:
    """Jobs who are either in one of the running states or pending but already sent to kubernetes."""
    return [
        job
        for job in jobs
        if job.status
        in [
            Status.initializing,
            Status.parsing,
            Status.running,
            Status.post_processing,
            Status.retrying,
        ]
        or (job.status == Status.pending and job.submitted_to_k8s)
    ]
