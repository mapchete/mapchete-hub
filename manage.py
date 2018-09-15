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
import os

import mapchete_hub
import mapchete_hub.log
from mapchete_hub.application import flask_app
from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import host_options, flask_options
from mapchete_hub.monitor import status_monitor


def _set_log_level(ctx, param, loglevel):
    mapchete_hub.log.set_log_level(loglevel)
    return loglevel


def _setup_logfile(ctx, param, logfile):
    if logfile:
        mapchete_hub.log.setup_logfile(logfile)
    return logfile


opt_loglevel = click.option(
    '--loglevel', type=click.Choice(['INFO', 'DEBUG', 'ERROR']), default='ERROR',
    callback=_set_log_level
)
opt_logfile = click.option('--logfile', type=click.Path(), default=None)


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@cli.command(short_help='Launches Flask Development Server.')
@opt_loglevel
@opt_logfile
@click.pass_context
def devserver(ctx, loglevel, logfile):
    click.echo("launch dev server")
    app = flask_app()
    app.run(host=host_options['host_ip'], port=host_options['port'])


@cli.command(short_help='Launch job status monitor.')
@opt_loglevel
@opt_logfile
@click.pass_context
def monitor(ctx, loglevel, logfile):
    click.echo("launch monitor")
    celery_app.conf.update(flask_options)
    celery_app.init_app(flask_app())
    status_monitor(celery_app)


@cli.command(short_help='Launches Celery zone worker.')
@opt_loglevel
@opt_logfile
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
        '-Ofair',
        '-Q', 'zone_queue'
    ]
    with app.app_context():
        return celery_main(celery_args)


@cli.command(short_help='Launches Celery subprocess worker.')
@opt_loglevel
@opt_logfile
@click.pass_context
def start_subprocess_worker(ctx, loglevel, logfile):
    click.echo("launch subprocess worker")
    app = flask_app()
    celery_args = [
        'celery',
        'worker',
        '-n', 'subprocess_worker@' + os.environ.get('HOST_IP', '%h'),
        '--without-gossip',
        '--max-tasks-per-child=1',
        '--concurrency=1',
        '-E',
        '--prefetch-multiplier=1',
        '-Ofair',
        '-Q', 'subprocess_queue'
    ]
    with app.app_context():
        return celery_main(celery_args)


@cli.command(short_help='Launches Celery preview worker.')
@opt_loglevel
@opt_logfile
@click.pass_context
def start_preview_worker(ctx, loglevel, logfile):
    click.echo("launch preview worker")
    app = flask_app()
    celery_args = [
        'celery',
        'worker',
        '-n', 'preview_worker@' + os.environ.get('HOST_IP', '%h'),
        '--without-gossip',
        '--max-tasks-per-child=1',
        '--concurrency=1',
        '-E',
        '--prefetch-multiplier=1',
        '-Ofair',
        '-Q', 'preview_queue'
    ]
    with app.app_context():
        return celery_main(celery_args)


if __name__ == '__main__':
    cli()
