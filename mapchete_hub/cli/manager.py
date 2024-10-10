from datetime import datetime
import logging
import time
from typing import List

import click
from mapchete.enums import Status

from mapchete_hub import __version__
from mapchete_hub.db import init_backenddb
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

    with init_backenddb(mhub_settings.backend_db) as backend_db:
        while True:
            all_jobs = backend_db.jobs(
                from_date=date_to_str(passed_time_to_timestamp(since))
            )
            queued = queued_jobs(
                jobs=all_jobs,
            )
            if queued:
                for job in queued:
                    click.echo(job)
            else:
                click.echo(
                    f"{datetime.now()}: no queued jobs found{f', next check in {watch_interval}' if watch else ''}"
                )

            if watch:
                time.sleep(interval_to_timedelta(watch_interval).seconds)
                continue
            else:
                break


def jobs_by_statuses(
    jobs: List[JobEntry], statuses: List[Status] = list(Status)
) -> List[JobEntry]:
    return [job for job in jobs if job.status in statuses]


def queued_jobs(jobs: List[JobEntry]) -> List[JobEntry]:
    return jobs_by_statuses(jobs, statuses=[Status.pending])
