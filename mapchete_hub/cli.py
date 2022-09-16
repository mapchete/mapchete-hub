"""Mapchete command line tool with subcommands."""

import click
from dask.distributed import LocalCluster
from mapchete.log import all_mapchete_packages
import mongomock.database
import os
import uvicorn

from mapchete_hub import __version__
from mapchete_hub.app import app, get_backend_db, get_dask_cluster_setup
from mapchete_hub.db import BackendDB


@click.version_option(version=__version__, message="%(version)s")
@click.group()
def main():  # pragma: no cover
    pass


@main.command(help="Start a mapchete Hub server instance.")
@click.option(
    "--host",
    type=click.STRING,
    default="127.0.0.1",
    help="Bind socket to this host. (default: 127.0.0.1)",
)
@click.option(
    "--port",
    type=click.INT,
    default=os.environ.get("MHUB_PORT", 5000),
    help="Bind socket to this port. (default: MHUB_PORT evironment variable or 5000)",
)
@click.option(
    "--add-mapchete-logger",
    is_flag=True,
    help="Adds mapchete logger to uvicorn logger.",
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
def start(
    host=None, port=None, log_level="error", add_mapchete_logger=False
):  # pragma: no cover

    # set up logging
    log_level = log_level.upper()
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s %(levelname)s %(name)s %(message)s"
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s %(levelname)s %(name)s %(message)s"
    cfg = dict(handlers=["default"], level=log_level)

    # add mapchete packages to default log handler
    if (
        add_mapchete_logger
        or os.environ.get("MHUB_ADD_MAPCHETE_LOGGER", "").lower() == "true"
    ):
        for i in all_mapchete_packages:
            log_config["loggers"][i] = cfg
    # add mapchete hub to default log handler
    log_config["loggers"]["mapchete_hub"] = cfg

    # start server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        log_config=log_config,
    )
