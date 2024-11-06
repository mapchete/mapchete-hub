"""Mapchete command line tool with subcommands."""

import os
from typing import Optional

import click
import uvicorn

from mapchete_hub import __version__
from mapchete_hub._log import uvicorn_log_config
from mapchete_hub.app import app
from mapchete_hub.settings import mhub_settings, LogLevels


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
    help="Adds mapchete loggers.",
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
    "--workers",
    "-w",
    type=click.INT,
    default=1,
    show_default=True,
    help="Number of uvicorn workers.",
)
def start(
    host: str,
    port: int,
    log_level: Optional[LogLevels] = None,
    add_mapchete_logger: bool = False,
    workers: int = 1,
):  # pragma: no cover
    # start server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=(log_level or mhub_settings.log_level).lower(),
        log_config=uvicorn_log_config(
            log_level=log_level, add_mapchete_logger=add_mapchete_logger
        ),
        workers=workers,
    )
