import click
from mapchete import Timer
from mapchete.cli.utils import opt_debug
from tqdm import tqdm

import mapchete_hub
from mapchete_hub.api import API, job_states
from mapchete_hub.config import host_options
from mapchete_hub.exceptions import JobFailed

# https://github.com/tqdm/tqdm/issues/481
tqdm.monitor_interval = 0


@click.version_option(version=mapchete_hub.__version__, message='%(version)s')
@click.group(help="Process control on Mapchete Hub.")
@click.option(
    '--host', '-h',
    type=click.STRING,
    nargs=1,
    default='%s:%s' % (host_options["host_ip"], host_options["port"]),
    help="Address and port of mhub endpoint (default: %s:%s)." % (
        host_options["host_ip"], host_options["port"]
    )
)
@click.pass_context
def mhub(ctx, **kwargs):
    ctx.obj = dict(**kwargs)


@mhub.command(short_help='Show capabilities.')
@click.pass_context
def capabilities(ctx):
    click.echo("mapchete hub capabilities (available processes, workers.)")


@mhub.command(short_help='Starts job.')
@click.argument('job_id', type=click.STRING)
@click.argument('mapchete_file', type=click.STRING)
@click.option('--bounds', '-b', type=float, nargs=4)
@click.option(
    '--mode', '-m', type=click.Choice(["continue", "overwrite"]), default="overwrite"
)
@opt_debug
@click.pass_context
def start(ctx, job_id, mapchete_file, bounds=None, mode=None, debug=False):
    try:
        click.echo(
            "job state: %s" % API(host=ctx.obj["host"]).start_job(
                job_id,
                mapchete_file,
                bounds, mode=mode
            ).state
        )
        show_progress(ctx, job_id)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help='Shows job status.')
@click.argument('job_id', type=click.STRING)
@click.option('--geojson', is_flag=True)
@click.pass_context
def status(ctx, job_id, geojson=False):
    try:
        click.echo(
            API(host=ctx.obj["host"]).job(job_id, geojson=geojson)
            if geojson
            else API(host=ctx.obj["host"]).job(job_id)
        )
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help='Shows job progress.')
@click.argument('job_id', type=click.STRING)
@click.pass_context
def progress(ctx, job_id):
    try:
        show_progress(ctx, job_id)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help='Shows current jobs.')
@click.option('--geojson', is_flag=True)
@click.pass_context
def jobs(ctx, geojson=False):
    try:
        click.echo(
            API(host=ctx.obj["host"]).jobs(geojson=geojson)
            if geojson
            else "\n".join([
                "%s: %s" % (job_id, state)
                for job_id, state in API(host=ctx.obj["host"]).jobs_states().items()
            ])
        )
    except Exception as e:
        click.echo("Error: %s" % e)


def show_progress(ctx, job_id):
    try:
        states = API(host=ctx.obj["host"]).job_progress(job_id)
        i = next(states)
        if i["state"] == "SUCCESS":
            click.echo(
                "job %s successfully finished in %s" % (
                    job_id, Timer(elapsed=i["runtime"])
                )
            )
            return

        if i["state"] in job_states["doing"]:
            with tqdm(
                initial=i["progress_data"]["current"],
                total=i["progress_data"]["total"]
            ) as pbar:
                for i in states:
                    if (
                        i["progress_data"]["current"] and
                        pbar.last_print_n and
                        i["progress_data"]["current"] > pbar.last_print_n
                    ):
                        pbar.update(i["progress_data"]["current"] - pbar.last_print_n)
    except JobFailed as e:
        click.echo("Job %s failed" % job_id)
        click.echo(e)
        return
    except Exception as e:
        click.echo("Error: %s" % e)
        return
