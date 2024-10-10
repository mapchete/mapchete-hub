import logging
import time
from typing import List

import click
from mapchete.enums import Status

from mapchete_hub import __version__
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
def main(
    since: str = "7d",
    inactive_since: str = "5h",
    pending_since: str = "3d",
    check_inactive_dashboard: bool = True,
    watch: bool = False,
    watch_interval: str = "3s",
):
    if mhub_settings.backend_db == "memory":
        raise ValueError("this command does not work with an in-memory db!")

    with init_backenddb(mhub_settings.backend_db) as status_handler:
        with KubernetesWorkerJobHandler.from_settings(
            status_handler=status_handler, settings=mhub_settings
        ) as job_handler:
            while True:
                # get all jobs from given time range at once to avoid unnecessary requests to DB
                all_jobs = status_handler.jobs(
                    from_date=date_to_str(passed_time_to_timestamp(since))
                )
                currently_running = len(running_jobs(all_jobs))
                currently_queued = queued_jobs(jobs=all_jobs)

                for job in currently_queued:
                    click.echo(
                        f"{currently_running}/{mhub_settings.max_parallel_jobs} jobs currently runnning"
                    )
                    if currently_running < mhub_settings.max_parallel_jobs:
                        click.echo(f"submitting job {job.job_id} to cluster")
                        job_handler.submit(job)
                        currently_running += 1
                    else:
                        click.echo("maximum limit of running jobs reached")
                        break

                if watch:
                    click.echo(f"next check in {watch_interval}")
                    time.sleep(interval_to_timedelta(watch_interval).seconds)
                else:
                    break


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
