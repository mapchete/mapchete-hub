import logging
import time
from typing import List

import click

from mapchete_hub import __version__
from mapchete_hub._log import setup_logger, LogLevels
from mapchete_hub.db import init_backenddb
from mapchete_hub.job_handler import KubernetesWorkerJobHandler
from mapchete_hub.job_handler.k8s_worker import K8SJobEntry
from mapchete_hub.settings import mhub_settings
from mapchete_hub.timetools import (
    date_to_str,
    interval_to_timedelta,
    passed_time_to_timestamp,
)

logger = logging.getLogger(__name__)


@click.version_option(version=__version__, message="%(version)s")
@click.group()
def main():  # pragma: no cover
    pass


@main.command()
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
    "--watch-interval", "-i", type=click.STRING, default="3s", show_default=True
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "notset"],
        case_sensitive=False,
    ),
    help="Set log level.",
)
@click.option(
    "--add-mapchete-logger",
    is_flag=True,
    help="Adds mapchete loggers.",
)
def watch(
    since: str = "7d",
    inactive_since: str = "5h",
    check_inactive_dashboard: bool = True,
    watch_interval: str = "3s",
    log_level: LogLevels = "info",
    add_mapchete_logger: bool = False,
):
    setup_logger(log_level, add_mapchete_logger=add_mapchete_logger)
    logger.info("mhub-manager online")

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
                    all_jobs = job_handler.jobs(
                        from_date=date_to_str(passed_time_to_timestamp(since))
                    )
                    logger.info(
                        "%s/%s jobs running (%s queued)",
                        len(running_jobs(all_jobs)),
                        mhub_settings.max_parallel_jobs,
                        len(queued_jobs(all_jobs)),
                    )

                    # check on running jobs and retry them if they are stalled
                    all_jobs = retry_stalled_jobs(
                        jobs=all_jobs,
                        inactive_since=inactive_since,
                        check_inactive_dashboard=check_inactive_dashboard,
                    )

                    # submit jobs waiting in queue
                    all_jobs = submit_pending_jobs(
                        jobs=all_jobs, job_handler=job_handler
                    )

                    logger.info("next check in %s", watch_interval)
                    time.sleep(interval_to_timedelta(watch_interval).seconds)
    except Exception as exc:
        logger.exception(exc)
        raise


@main.command()
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
    "--log-level",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "notset"],
        case_sensitive=False,
    ),
    help="Set log level.",
)
@click.option(
    "--add-mapchete-logger",
    is_flag=True,
    help="Adds mapchete loggers.",
)
def clean(
    since: str = "7d",
    inactive_since: str = "5h",
    check_inactive_dashboard: bool = True,
    log_level: LogLevels = "info",
    add_mapchete_logger: bool = False,
):
    setup_logger(log_level, add_mapchete_logger=add_mapchete_logger)
    logger.info("mhub-manager online")

    try:
        if mhub_settings.backend_db == "memory":
            raise ValueError("this command does not work with an in-memory db!")

        logger.debug("connecting to backend DB ...")
        with init_backenddb(mhub_settings.backend_db) as status_handler:
            logger.debug("creating KubernetesWorkerJobHandler ...")
            with KubernetesWorkerJobHandler.from_settings(
                status_handler=status_handler, settings=mhub_settings
            ) as job_handler:
                # check on running jobs and retry them if they are stalled
                retry_stalled_jobs(
                    jobs=job_handler.jobs(
                        from_date=date_to_str(passed_time_to_timestamp(since))
                    ),
                    inactive_since=inactive_since,
                    check_inactive_dashboard=check_inactive_dashboard,
                )

    except Exception as exc:
        logger.exception(exc)
        raise


def retry_stalled_jobs(
    jobs: List[K8SJobEntry],
    inactive_since: str = "5h",
    check_inactive_dashboard: bool = True,
) -> List[K8SJobEntry]:
    # this only affects currently running jobs, so the maximum parallel jobs would not be exceeded
    logger.debug("found %s jobs", len(jobs))
    for job in jobs:
        if job.is_stalled(
            inactive_since=inactive_since,
            check_inactive_dashboard=check_inactive_dashboard,
        ):
            if job.k8s_is_failed_or_gone():
                try:
                    job.k8s_retry()
                except Exception as exc:
                    logger.exception(exc)
                    logger.error("error when handling kubernetes job")
            else:
                logger.debug(
                    "%s: job seems to be inactive, but kubernetes job has not failed yet",
                    job.job_id,
                )
    return jobs


def submit_pending_jobs(
    jobs: List[K8SJobEntry], job_handler: KubernetesWorkerJobHandler
) -> List[K8SJobEntry]:
    # determine jobs
    currently_running_count = len(running_jobs(jobs))
    logger.debug("currently %s jobs running", currently_running_count)
    currently_queued_count = len(queued_jobs(jobs=jobs))
    logger.debug("currently %s jobs queued", currently_queued_count)

    if currently_running_count >= mhub_settings.max_parallel_jobs:
        logger.info(
            "%s/%s jobs currently running, nothing to submit",
            currently_running_count,
            mhub_settings.max_parallel_jobs,
        )
        return jobs

    # iterate to queued jobs and try to submit them
    for job in jobs:
        if job.is_queued():
            if currently_running_count < mhub_settings.max_parallel_jobs:
                try:
                    job.k8s_submit()
                    currently_running_count += 1
                    logger.info(
                        "submitted job %s to cluster (%s/%s running)",
                        job.job_id,
                        currently_running_count,
                        mhub_settings.max_parallel_jobs,
                    )
                    logger.debug(
                        "this is not my responsibility anymore but I'll keep my eyes on that"
                    )
                except Exception as exc:
                    logger.exception(exc)
            else:
                logger.debug("maximum limit of running jobs reached")
        jobs.append(job)
    return jobs


def queued_jobs(jobs: List[K8SJobEntry]) -> List[K8SJobEntry]:
    """Get jobs who are in pending state and not yet sent to kubernetes."""
    return [job for job in jobs if job.is_queued()]


def running_jobs(jobs: List[K8SJobEntry]) -> List[K8SJobEntry]:
    """Jobs who are either in one of the running states or pending but already sent to kubernetes."""
    return [job for job in jobs if job.has_active_status()]
