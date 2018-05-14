from celery.bin.celery import main as celery_main
import click
import json
import time
from urllib import request
from urllib.error import URLError

import mapchete_hub
from mapchete_hub.config import get_host_options


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group()
@click.pass_context
def mhub(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@mhub.command(short_help='Show capabilities.')
@click.pass_context
def capabilities(ctx):
    click.echo("mapchete hub capabilities (available processes, workers.)")


@mhub.command(short_help='Starts job.')
@click.argument('job_name', type=str)
@click.pass_context
def start(ctx, job_name):
    try:
        start_job(job_name)
    except URLError:
        click.echo("No mapchete hub running under given endpoint.")


@mhub.command(short_help='Stops job.')
@click.argument('job_name', type=str)
@click.pass_context
def stop(ctx):
    click.echo("stop job")


@mhub.command(short_help='Shows job status.')
@click.argument('job_name', type=str)
@click.pass_context
def status(ctx, job_name):
    try:
        get_status(job_name)
    except URLError:
        click.echo("No mapchete hub running under given endpoint.")


@mhub.command(short_help='Shows current tasks.')
@click.pass_context
def tasks(ctx):
    return get_tasks()


def start_job(job_name):
    host_opts = get_host_options()
    url = "http://%s:%s/start/%s" % (host_opts["host_ip"], host_opts["port"], job_name)
    res = request.urlopen(url).read()
    click.echo(res)


def get_status(job_name):
    host_opts = get_host_options()
    url = "http://%s:%s/status/%s" % (host_opts["host_ip"], host_opts["port"], job_name)
    while True:
        res = json.loads(request.urlopen(url).read().decode())
        status = res["status"]
        ready = status in ["SUCCESS", "FAILURE"]
        click.echo(status)
        if ready:
            break
        time.sleep(1)


def get_tasks():
    celery_args = [
        'celery',
        'inspect',
        'active'
    ]
    return celery_main(celery_args)
