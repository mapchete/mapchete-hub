import click
import click_spinner
import datetime
import logging
from mapchete import Timer
from mapchete.cli import utils
from tqdm import tqdm
import warnings

import mapchete_hub
from mapchete_hub.api import API, job_states
from mapchete_hub.application import process_area_from_config
from mapchete_hub.config import host_options
from mapchete_hub.exceptions import JobFailed
from mapchete_hub import log

# https://github.com/tqdm/tqdm/issues/481
tqdm.monitor_interval = 0


def _set_debug_log_level(ctx, param, debug):
    if debug:
        log.set_log_level(logging.DEBUG)
    return debug


opt_debug = click.option(
    "--debug", "-d",
    is_flag=True,
    callback=_set_debug_log_level,
    help="Print debug log output."
)
opt_geojson = click.option(
    "--geojson",
    is_flag=True,
    help="Print as GeoJSON"
)


@click.version_option(version=mapchete_hub.__version__, message="%(version)s")
@click.group(help="Process control on Mapchete Hub.")
@click.option(
    "--host", "-h",
    type=click.STRING,
    nargs=1,
    default="%s:%s" % (host_options["host_ip"], host_options["port"]),
    help="Address and port of mhub endpoint (default: %s:%s)." % (
        host_options["host_ip"], host_options["port"]
    )
)
@click.pass_context
def mhub(ctx, **kwargs):
    """Main command group."""
    ctx.obj = dict(**kwargs)


@mhub.command(short_help="Show available processes.")
@click.option(
    "--process_name", "-n", type=click.STRING, help="Print docstring of process."
)
@click.option(
    "--docstrings", is_flag=True, help="Print docstrings of all processes."
)
@click.pass_context
def processes(ctx, process_name=None, docstrings=False):
    """Show available processes."""
    def _print_process_info(process_module, docstrings=False):
        click.echo(
            click.style(
                process_module["name"],
                bold=docstrings,
                underline=docstrings
            )
        )
        if docstrings:
            click.echo(process_module["docstring"])

    try:
        res = API(host=ctx.obj["host"]).get("capabilities.json")
        if res.status_code != 200:
            raise ConnectionError(res.json)
        cap = res.json

        # get all registered processes
        processes = cap.get("processes")

        # print selected process
        if process_name:
            _print_process_info(processes[process_name], docstrings=True)
        else:
            # print all processes
            click.echo("%s processes found" % len(processes))
            for process_name in sorted(processes.keys()):
                _print_process_info(processes[process_name], docstrings=docstrings)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show available queues and workers.")
@click.pass_context
def queues(ctx):
    """Show available queues and workers."""
    try:
        res = API(host=ctx.obj["host"]).get("capabilities.json")
        if res.status_code != 200:
            raise ConnectionError(res.json)
        if res.json["queues"]:
            for queue, workers in res.json["queues"].items():
                click.echo("%s:" % queue)
                for worker in workers:
                    click.echo("    %s" % worker)
        else:
            click.echo("no queues nor workers currently registered")
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(help="Execute a process.")
@utils.arg_mapchete_files
@utils.opt_zoom
@utils.opt_bounds
@utils.opt_point
@utils.opt_wkt_geometry
@utils.opt_tile
@utils.opt_overwrite
@utils.opt_verbose
@opt_debug
@click.option(
    "--queue", "-q",
    type=click.STRING,
    default="execute_queue",
    help="Queue the job should be added to."
)
@click.pass_context
def execute(
    ctx,
    mapchete_files,
    overwrite=False,
    verbose=False,
    queue=None,
    **kwargs
):
    """Execute a process."""
    for mapchete_file in mapchete_files:
        try:
            job = API(host=ctx.obj["host"]).start_job(
                mapchete_file,
                mode="overwrite" if overwrite else "continue",
                mhub_worker="execute_worker",
                mhub_queue=queue,
                **kwargs
            )
            if verbose:
                click.echo("job %s state: %s" % (job.job_id, job.state))
                _show_progress(ctx, job.job_id)
            else:
                click.echo(job.job_id)
        except Exception as e:
            click.echo("Error: %s" % e)


@mhub.command(help="Create index of output tiles.")
@utils.arg_mapchete_files
@utils.opt_zoom
@utils.opt_bounds
@utils.opt_point
@utils.opt_wkt_geometry
@utils.opt_tile
@utils.opt_verbose
@click.option(
    "--queue", "-q",
    type=click.STRING,
    default="index_queue",
    help="Queue the job should be added to."
)
@click.pass_context
def index(
    ctx,
    mapchete_files,
    verbose=False,
    queue=None,
    **kwargs
):
    """Create index of output tiles."""
    for mapchete_file in mapchete_files:
        try:
            job = API(host=ctx.obj["host"]).start_job(
                mapchete_file,
                mhub_worker="index_worker",
                mhub_queue=queue,
                **kwargs
            )
            if verbose:
                click.echo("job %s state: %s" % (job.job_id, job.state))
                _show_progress(ctx, job.job_id)
            else:
                click.echo(job.job_id)
        except Exception as e:
            click.echo("Error: %s" % e)


@mhub.command(short_help="Start job. (deprecated)")
@click.argument("job_id", type=click.STRING)
@click.argument("mapchete_file", type=click.STRING)
@click.option("--bounds", "-b", type=float, nargs=4)
@click.option(
    "--mode", "-m",
    type=click.Choice(["continue", "overwrite"]),
    default="overwrite"
)
@utils.opt_debug
@click.pass_context
def start(ctx, job_id, mapchete_file, bounds=None, mode=None, debug=False):
    """Start job."""
    warnings.warn(DeprecationWarning(
        "This command will be deprecated. Please use `mhub execute` instead."
    ))
    try:
        click.echo(
            "job %s state: %s" % (
                job_id,
                API(host=ctx.obj["host"]).start_job(
                    mapchete_file,
                    job_id=job_id,
                    bounds=bounds,
                    mode=mode
                ).state
            )
        )
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show job status.")
@click.argument("job_id", type=click.STRING)
@opt_geojson
@click.option(
    "--traceback",
    is_flag=True,
    help="Print only traceback if available."
)
@click.pass_context
def status(ctx, job_id, geojson=False, traceback=False):
    """Show job status."""
    try:
        response = (
            API(host=ctx.obj["host"]).job(job_id, geojson=geojson)
            if geojson
            else API(host=ctx.obj["host"]).job(job_id)
        )
        if geojson:
            click.echo(response)
        elif traceback:
            click.echo(response.json["properties"]["traceback"])
        else:
            _print_job_details(response)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show job progress.")
@click.argument("job_id", type=click.STRING)
@click.pass_context
def progress(ctx, job_id):
    """Show job progress."""
    try:
        _show_progress(ctx, job_id)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show current jobs.")
@opt_geojson
@click.option(
    "--output_path",
    type=click.STRING,
    help="only print jobs with specific output_path"
)
@click.pass_context
def jobs(ctx, geojson=False, output_path=None):
    """Show current jobs."""
    try:
        if geojson:
            click.echo(
                API(host=ctx.obj["host"]).jobs(geojson=True, output_path=output_path)
            )
        else:
            # sort by state and then by timestamp
            jobs = sorted(
                API(host=ctx.obj["host"]).jobs(output_path=output_path).values(),
                key=lambda x: (
                    x.json["properties"]["state"],
                    x.json["properties"]["timestamp"]
                )
            )
            for i in jobs:
                print(i)
                _print_job_details(i)
                click.echo("")
    except Exception as e:
        click.echo("Error: %s" % e)


def _print_job_details(job):
    for group, states in job_states.items():
        for state in states:
            if job.state == state:
                if group == "todo":
                    color = "blue"
                elif group == "doing":
                    color = "yellow"
                elif state == "SUCCESS":
                    color = "green"
                elif state == "FAILURE":
                    color = "red"
    properties = job.json["properties"]
    properties["config"] = properties["config"] or {}
    mapchete_config = properties.get("config", {}).get("mapchete_config", {})

    # job ID and job state
    click.echo(click.style("%s: %s" % (job.job_id, job.state), fg=color, bold=True))

    # command
    click.echo(
        "command: %s" % mapchete_config.get("mhub_worker", "None").replace("_worker", "")
    )

    # queue
    click.echo("queue: %s" % mapchete_config.get("mhub_queue"))

    # output path
    click.echo("output path: %s" % mapchete_config.get("output", {}).get("path"))

    # bounds
    try:
        bounds = ", ".join(
            map(str, process_area_from_config(properties["config"]).bounds)
        )
    except:
        bounds = None
    click.echo("process bounds: %s" % bounds)

    # start time
    click.echo(
        "started: %s" % (
            datetime.datetime.utcfromtimestamp(
                properties.get("started")
            ).strftime('%Y-%m-%d %H:%M:%S') if properties.get("started") else None
        )
    )

    # runtime
    runtime = properties.get("runtime")
    click.echo(
        "runtime: %s" % (Timer(runtime) if runtime else None)
    )

    # last received update
    click.echo(
        "last received update: %s" % datetime.datetime.utcfromtimestamp(
            properties.get("timestamp")
        ).strftime('%Y-%m-%d %H:%M:%S')
    )


def _show_progress(ctx, job_id):
    try:
        with click_spinner.spinner():
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
