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
import os

import mapchete_hub
from mapchete_hub.application import flask_app
from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import host_options, flask_options
from mapchete_hub.monitor import status_monitor


# lower stream output log level
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.ERROR)
logging.getLogger().addHandler(stream_handler)


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@cli.command(short_help='Launches Flask Development Server.')
@click.option('--loglevel', type=click.Choice(['INFO', 'DEBUG']), default=None)
@click.option('--logfile', type=click.Path(), default=None)
@click.pass_context
def devserver(ctx, loglevel, logfile):
    click.echo("launch dev server")
    setup_logger(loglevel, logfile)
    app = flask_app()
    app.run(host=host_options['host_ip'], port=host_options['port'])


@cli.command(short_help='Launch job status monitor.')
@click.option('--loglevel', type=click.Choice(['INFO', 'DEBUG']), default=None)
@click.option('--logfile', type=click.Path(), default=None)
@click.pass_context
def monitor(ctx, loglevel, logfile):
    click.echo("launch monitor")
    setup_logger(loglevel, logfile)
    celery_app.conf.update(flask_options)
    celery_app.init_app(flask_app())
    status_monitor(celery_app)


@cli.command(short_help='Launches Celery zone worker.')
@click.option('--loglevel', type=click.Choice(['INFO', 'DEBUG']), default=None)
@click.option('--logfile', type=click.Path(), default=None)
@click.pass_context
def start_zone_worker(ctx, loglevel, logfile):
    click.echo("launch zone worker")
    app = flask_app()
    celery_args = [
        'celery',
        'worker',
        '-n', 'zone_worker@' + os.environ.get('HOST_IP', '%h'),
        '--without-gossip',
        '--max-tasks-per-child=1',
        '--concurrency=1',
        '-E',
        '--prefetch-multiplier=1',
        '-Q', 'zone_queue'
    ]
    if loglevel:
        celery_args.append('--loglevel=%s' % loglevel)
    if logfile:
        celery_args.append('--logfile=%s' % logfile)
    with app.app_context():
        return celery_main(celery_args)


def setup_logger(loglevel=None, logfile=None):
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        logging.getLogger("mapchete_hub").setLevel(logging.DEBUG)
    if loglevel == "DEBUG":
        logging.getLogger("mapchete_hub").setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)
    elif loglevel == "INFO":
        logging.getLogger("mapchete_hub").setLevel(logging.INFO)
        stream_handler.setLevel(logging.INFO)


if __name__ == '__main__':
    cli()
