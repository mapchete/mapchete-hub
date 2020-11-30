#!/usr/bin/env python3
"""
Main entry point for mapcheteHub.

To start a mapcheteHub cluster, you have to start
- a server instance (currently just devserver available)
- a monitor instance
- one or more workers

Inspirations:
https://github.com/Robpol86/Flask-Large-Application-Example/blob/master/manage.py
"""
from celery.bin.celery import main as celery_main
import click
import logging
from mapchete_hub import log
import os

import mapchete_hub
from mapchete_hub.celery_app import celery_app
from mapchete_hub.flask_app import flask_app
from mapchete_hub.monitor import status_monitor


logger = logging.getLogger(__name__)


def _set_log_level(ctx, param, loglevel):
    log.set_log_level(loglevel)
    return loglevel


def _setup_logfile(ctx, param, logfile):
    if logfile:
        log.setup_logfile(logfile)
    return logfile


opt_loglevel = click.option(
    '--loglevel',
    type=click.Choice(['INFO', 'DEBUG', 'ERROR']),
    default='ERROR',
    callback=_set_log_level
)
opt_logfile = click.option(
    '--logfile',
    type=click.Path(),
    default=None,
    callback=_setup_logfile
)


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@cli.command(short_help='Launches Flask Development Server.')
@opt_loglevel
@opt_logfile
@click.pass_context
def devserver(ctx, **kwargs):
    click.echo("launch devserver")
    flask_app().run(host="127.0.0.1", port="5000")


@cli.command(short_help='Launch job status monitor.')
@opt_loglevel
@opt_logfile
@click.pass_context
def monitor(ctx, **kwargs):
    click.echo("launch monitor")
    logger.debug("init app and start monitor")
    app = flask_app()
    celery_app.conf.update(app.config)
    celery_app.init_app(app)
    status_monitor(celery_app)


@cli.command(short_help='Launches Celery worker.')
@click.option(
    "--worker-name", "-n",
    default="execute_worker",
    help="Worker type to be spawned."
)
@click.option(
    "--queues", "-q",
    type=click.STRING,
    default="execute_queue",
    help="Queue(s) worker should listen to."
)
@opt_loglevel
@opt_logfile
@click.pass_context
def worker(ctx, worker_name, queues, **kwargs):
    click.echo("launch %s attatched to queue(s) %s" % (worker_name, queues))
    app = flask_app(full=False)
    with app.app_context():
        return celery_main(
            [
                'celery',
                'worker',
                '-n', '%s@%s' % (worker_name, os.environ.get('HOST_IP', '%h')),
                '--without-gossip',
                '--max-tasks-per-child=1',
                '--concurrency=1',
                '-E',
                '--prefetch-multiplier=1',
                '-Ofair',
                '-Q', queues
            ]
        )


if __name__ == '__main__':
    cli()
