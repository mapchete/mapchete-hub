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
def main():
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
@click.option("--debug", is_flag=True)
def start(host=None, port=None, debug=False):

    # set up logging
    log_level = "debug" if debug else "error"
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s %(levelname)s %(name)s %(message)s"
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s %(levelname)s %(name)s %(message)s"

    # add mapchete packages and mapchete hub to default log handler
    cfg = dict(handlers=["default"], level=log_level.upper())
    for i in all_mapchete_packages:
        log_config["loggers"][i] = cfg
    log_config["loggers"]["mapchete_hub"] = cfg

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        log_config=log_config,
    )
