import logging
import time
from typing import List, Set

import click
from mapchete.enums import Status
import requests

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
                    all_jobs = status_handler.jobs(
                        from_date=date_to_str(passed_time_to_timestamp(since))
                    )

                    # check on running jobs and retry them if they are stalled
                    all_jobs = retry_stalled_jobs(
                        jobs=all_jobs,
                        job_handler=job_handler,
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
                    jobs=status_handler.jobs(
                        from_date=date_to_str(passed_time_to_timestamp(since))
                    ),
                    job_handler=job_handler,
                    inactive_since=inactive_since,
                    check_inactive_dashboard=check_inactive_dashboard,
                )

    except Exception as exc:
        logger.exception(exc)
        raise


def retry_stalled_jobs(
    jobs: List[JobEntry],
    job_handler: KubernetesWorkerJobHandler,
    inactive_since: str = "5h",
    check_inactive_dashboard: bool = True,
) -> List[JobEntry]:
    # this only affects currently running jobs, so the maximum parallel jobs would not be exceeded
    def _resubmit_if_failed(job: JobEntry) -> JobEntry:
        k8s_job_status = job_handler.job_status(job)

        if k8s_job_status.is_failed():
            observers = job_handler.get_job_observers(job)
            remaining_retries = (
                mhub_settings.k8s_retry_job_x_times + 1
            ) - job.k8s_attempts

            if remaining_retries <= 0:
                logger.info(
                    "maximum retries (%s) already met (%s)",
                    mhub_settings.k8s_retry_job_x_times,
                    job.k8s_attempts,
                )
                observers.notify(
                    status=Status.failed,
                    exception=RuntimeError("too many kubernetes job attempts failed"),
                )
                job.status = Status.failed
                return job

            observers.notify(
                status=Status.retrying,
                message=f"kubernetes job run failed (remaining retries: {remaining_retries})",
            )
            logger.info(
                "%s: kubernetes job has failed, resubmitting to cluster:", job.job_id
            )
            return job_handler.submit(job)

        logger.info(
            "%s: job seems to be inactive, but kubernetes job %s has not failed yet: %s",
            job.job_id,
            k8s_job_status,
        )
        return job

    logger.info("found %s jobs", len(jobs))

    out_jobs = []
    running = running_jobs(jobs)

    for job in jobs:
        # check if inactive for too long
        if (
            job.job_id in running
            and job.updated
            and passed_time_to_timestamp(inactive_since) > job.updated
        ):
            logger.debug(
                "%s: %s but has been inactive since %s",
                job.job_id,
                job.status,
                job.updated,
            )
            try:
                out_jobs.append(_resubmit_if_failed(job))
            except Exception as exc:
                logger.exception(exc)
                logger.error("error when handling kubernetes job")
                out_jobs.append(job)

        # running jobs with unavailable dashboard
        # NOTE: jobs can be running without having a dashboard
        elif (
            check_inactive_dashboard
            and job.job_id in running
            and job.dask_dashboard_link
            and requests.get(job.dask_dashboard_link).status_code != 200
        ):
            logger.debug(
                "%s: %s but dashboard %s does not have a status code of 200",
                job.job_id,
                job.status,
                job.dask_dashboard_link,
            )
            try:
                out_jobs.append(_resubmit_if_failed(job))
            except Exception as exc:
                logger.exception(exc)
                logger.error("error when handling kubernetes job")
                out_jobs.append(job)

        else:
            out_jobs.append(job)

    return out_jobs


def submit_pending_jobs(
    jobs: List[JobEntry], job_handler: KubernetesWorkerJobHandler
) -> List[JobEntry]:
    out_jobs = []

    # determine jobs
    currently_running_count = len(running_jobs(jobs))
    logger.debug("currently %s jobs running", currently_running_count)
    currently_queued = queued_jobs(jobs=jobs)
    logger.debug("currently %s jobs queued", len(currently_queued))

    # iterate to queued jobs and try to submit them
    for job in jobs:
        if job.job_id in currently_queued:
            logger.info(
                f"{currently_running_count}/{mhub_settings.max_parallel_jobs} jobs currently runnning"
            )
            if currently_running_count < mhub_settings.max_parallel_jobs:
                logger.info("submitting job %s to cluster", job.job_id)
                try:
                    out_jobs.append(job_handler.submit(job))
                    currently_running_count += 1
                    logger.debug(
                        "this is not my responsibility anymore but I'll keep my eyes on that"
                    )
                except Exception as exc:
                    logger.exception(exc)
                    out_jobs.append(job)
            else:
                logger.info("maximum limit of running jobs reached")
                out_jobs.append(job)
        else:
            out_jobs.append(job)
    return out_jobs


def queued_jobs(jobs: List[JobEntry]) -> Set[str]:
    """Get jobs who are in pending state and not yet sent to kubernetes."""
    return set(
        [
            job.job_id
            for job in jobs
            if job.status == Status.pending and not job.submitted_to_k8s
        ]
    )


def running_jobs(jobs: List[JobEntry]) -> Set[str]:
    """Jobs who are either in one of the running states or pending but already sent to kubernetes."""
    return set(
        [
            job.job_id
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
    )
