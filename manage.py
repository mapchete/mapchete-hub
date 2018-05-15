#!/usr/bin/env python3
"""
Main entry point for mapcheteHub.

Inspirations:
https://github.com/Robpol86/Flask-Large-Application-Example/blob/master/manage.py
"""
from celery.bin.celery import main as celery_main
import click

import mapchete_hub
from mapchete_hub.config import get_host_options
from mapchete_hub.application import flask_app


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@cli.command(short_help='Launches Flask Development Server.')
@click.pass_context
def devserver(ctx):
    click.echo("launch dev server")
    app = flask_app()
    host_opts = get_host_options()
    app.run(host=host_opts['host_ip'], port=host_opts['port'])


@cli.command(short_help='Launches Celery tile worker.')
@click.pass_context
def start_tile_worker(ctx):
    click.echo("launch tile worker")
    raise NotImplementedError


@cli.command(short_help='Launches Celery zone worker.')
@click.option('--loglevel', type=click.Choice(['INFO', 'DEBUG']), default=None)
@click.pass_context
def start_zone_worker(ctx, loglevel):
    click.echo("launch zone worker")
    app = flask_app()
    celery_args = [
        'celery',
        'worker',
        '-n', 'zone_worker',
        '--without-gossip',
        '--max-tasks-per-child=1',
        '--concurrency=1',
        '-E',
        '--prefetch-multiplier=1',
        '-Q', 'zone_queue'
    ]
    if loglevel:
        celery_args.append('--loglevel=%s' % loglevel)
    with app.app_context():
        return celery_main(celery_args)


if __name__ == '__main__':
    cli()
