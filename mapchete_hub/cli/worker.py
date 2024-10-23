import logging

import click
from distributed import LocalCluster
from mapchete.commands.observer import Observers
from mapchete.enums import Status

from mapchete_hub import __version__
from mapchete_hub._log import LogLevels, setup_logger
from mapchete_hub.db import init_backenddb
from mapchete_hub.job_wrapper import job_wrapper
from mapchete_hub.observers import DBUpdater, SlackMessenger
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


@click.version_option(version=__version__, message="%(version)s")
@click.group()
def main():  # pragma: no cover
    pass


@main.command(help="Run a job from an mhub database.")
@click.argument("job-id", type=click.STRING)
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
def run_job(
    job_id: str, log_level: LogLevels = "info", add_mapchete_logger: bool = False
):
    """This will run a pending job."""
    setup_logger(log_level, add_mapchete_logger=add_mapchete_logger)

    try:
        if mhub_settings.backend_db == "memory":
            raise ValueError("this command does not work with an in-memory db!")

        logger.debug("connecting to backend DB ...")
        with init_backenddb(mhub_settings.backend_db) as backend_db:
            # read job entry from databast
            job_entry = backend_db.job(job_id)
            logger.debug("got job %s", job_entry)
            # only attempt to run job if its status is pending
            if job_entry.status == Status.pending:
                logger.debug("job is in pending status, setting up observers")
                # set up status updater observer
                job_db_updater = DBUpdater(
                    backend_db=backend_db,
                    job_entry=job_entry,
                    event_rate_limit=mhub_settings.backend_db_event_rate_limit,
                )
                # initialize slack messenger observer
                job_slack_messenger = SlackMessenger(
                    mhub_settings.self_instance_name,
                    job=job_entry,
                )
                observers = Observers([job_db_updater, job_slack_messenger])
                logger.debug("observers created: %s", observers)
                try:
                    if (
                        mhub_settings.dask_gateway_url is None
                        and mhub_settings.dask_scheduler_url is None
                    ):
                        logger.debug("initializing LocalCluster ...")
                        local_cluster = LocalCluster(
                            processes=False, n_workers=4, threads_per_worker=8
                        )
                    else:
                        local_cluster = None
                    job_wrapper(
                        job_entry,
                        observers=observers,
                        local_cluster=local_cluster,
                    )
                except Exception as exc:
                    logger.exception(exc)
                    observers.notify(status=Status.failed, exception=exc)
                    raise
            else:
                logger.debug(
                    "job %s cannot be run because it is in status %s",
                    job_id,
                    job_entry.status.value,
                )
    except Exception as exc:
        logger.exception(exc)
        raise
