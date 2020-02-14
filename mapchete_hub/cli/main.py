import click
import click_spinner
from datetime import datetime, timedelta
import logging
from mapchete import Timer
from mapchete.cli import utils
from shapely.geometry import shape
from tqdm import tqdm

from mapchete_hub import __version__
from mapchete_hub.api import API, job_states
from mapchete_hub.config import default_timeout, host_options
from mapchete_hub.exceptions import JobFailed
from mapchete_hub.log import set_log_level
from mapchete_hub._utils import str_to_date, date_to_str

# https://github.com/tqdm/tqdm/issues/481
tqdm.monitor_interval = 0


def _set_debug_log_level(ctx, param, debug):
    if debug:
        set_log_level(logging.DEBUG)
    return debug


def _get_timestamp(ctx, param, timestamp):
    """Convert timestamp to datetime object."""
    if timestamp:
        try:
            # for a convertable timestamp like '2019-11-01T15:00:00'
            timestamp = str_to_date(timestamp)
        except ValueError:
            # for a time range like '1d', '12h', '30m'
            try:
                time_types = {
                    "d": "days",
                    "h": "hours",
                    "m": "minutes",
                    "s": "seconds",
                }
                for k, v in time_types.items():
                    if timestamp.endswith(k):
                        timestamp = datetime.utcnow() - timedelta(
                            **{v: int(timestamp[:-1])}
                        )
                        break
                else:
                    raise ValueError()
            except ValueError:
                raise click.BadParameter(
                    """either provide a timestamp like '2019-11-01T15:00:00' or a time """
                    """range in the format '1d', '12h', '30m', etc."""
                )
        return date_to_str(timestamp)


opt_debug = click.option(
    "--debug", "-d",
    is_flag=True,
    callback=_set_debug_log_level,
    help="Print debug log output."
)
opt_geojson = click.option(
    "--geojson", "-g",
    is_flag=True,
    help="Print as GeoJSON."
)


@click.version_option(version=__version__, message="%(version)s")
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
@click.option(
    "--timeout",
    type=click.INT,
    default=default_timeout,
    help="Time in seconds to wait for server response. (default: %s)" % default_timeout,
)
@click.pass_context
def mhub(ctx, **kwargs):
    """Main command group."""
    ctx.obj = dict(**kwargs)


@mhub.command(short_help="Show remote package versions.")
@opt_debug
@click.pass_context
def remote_versions(ctx, **kwargs):
    """Print package versions installed on remote mapchete Hub."""
    try:
        res = API(**ctx.obj).get("capabilities.json")
        if res.status_code != 200:
            raise ConnectionError(res.json)
        click.echo("mapchete_hub: %s" % res.json["version"])
        click.echo("")
        for package, version in sorted(res.json["packages"].items()):
            click.echo("%s: %s" % (package, version))
    except Exception as e:
        click.echo("Error: %s" % e)
    ctx.exit()


@mhub.command(short_help="Show available processes.")
@click.option(
    "--process_name", "-n", type=click.STRING, help="Print docstring of process."
)
@click.option(
    "--docstrings", is_flag=True, help="Print docstrings of all processes."
)
@opt_debug
@click.pass_context
def processes(ctx, process_name=None, docstrings=False, **kwargs):
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
        res = API(**ctx.obj).get("capabilities.json")
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
@click.option(
    "--queue_name", "-n", type=click.STRING, help="Print detailed information on queue."
)
@opt_debug
@click.pass_context
def queues(ctx, queue_name=None, **kwargs):
    """Show available queues."""
    try:
        if queue_name:
            res = API(**ctx.obj).get("queues/%s" % queue_name)
            if res.status_code == 404:
                click.echo("no queue '%s' found" % queue_name)
            elif res.status_code != 200:
                raise ConnectionError(res.json)
            else:
                click.echo("workers (%s)" % res.json["worker_count"])
                for worker in res.json["workers"]:
                    click.echo("    %s" % worker)
                click.echo("jobs (%s in queue):" % res.json["job_count"])
                for status, jobs in res.json["jobs"].items():
                    click.echo("    %s:" % status)
                    for job in jobs:
                        click.echo("        %s" % job)
        else:
            res = API(**ctx.obj).get("queues")
            if res.status_code != 200:
                raise ConnectionError(res.json)
            if res.json.items():
                for queue, properties in res.json.items():
                    click.echo("%s:" % queue)
                    click.echo("    workers: %s" % properties["worker_count"])
                    click.echo("    pending jobs: %s" % properties["job_count"])
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
    debug=False,
    **kwargs
):
    """Execute a process."""
    for mapchete_file in mapchete_files:
        try:
            job = API(**ctx.obj).start_job(
                mapchete_config=mapchete_file,
                mode="overwrite" if overwrite else "continue",
                command="execute",
                **kwargs
            )
            if verbose:
                click.echo("job %s state: %s" % (job.job_id, job.state))
                _show_progress(ctx, job.job_id, disable=debug)
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
@opt_debug
@click.pass_context
def index(
    ctx,
    mapchete_files,
    verbose=False,
    queue=None,
    debug=False,
    **kwargs
):
    """Create index of output tiles."""
    for mapchete_file in mapchete_files:
        try:
            job = API(**ctx.obj).start_job(
                mapchete_config=mapchete_file,
                command="index",
                **kwargs
            )
            if verbose:
                click.echo("job %s state: %s" % (job.job_id, job.state))
                _show_progress(ctx, job.job_id, disable=debug)
            else:
                click.echo(job.job_id)
        except Exception as e:
            click.echo("Error: %s" % e)


@mhub.command(help="Execute a batch of processes.")
@click.argument("batch_file", type=click.Path(exists=True))
@utils.opt_bounds
@utils.opt_point
@utils.opt_wkt_geometry
@utils.opt_tile
@utils.opt_overwrite
@click.option(
    "--slack",
    is_flag=True,
    help="Post message to slack if batch completed successfully."
)
@utils.opt_verbose
@opt_debug
@click.pass_context
def batch(
    ctx,
    batch_file,
    overwrite=False,
    verbose=False,
    debug=False,
    **kwargs
):
    """Execute a batch of processes."""
    try:
        job = API(**ctx.obj).start_batch(
            batch=batch_file,
            mode="overwrite" if overwrite else "continue",
            **kwargs
        )
        if verbose:
            click.echo("job %s state: %s" % (job.job_id, job.state))
            _show_progress(ctx, job.job_id, disable=debug)
        else:
            click.echo(job.job_id)
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
@opt_debug
@click.pass_context
def status(ctx, job_id, geojson=False, traceback=False, **kwargs):
    """Show job status."""
    try:
        response = (
            API(**ctx.obj).job(job_id, geojson=geojson)
            if geojson
            else API(**ctx.obj).job(job_id)
        )
        if geojson:
            click.echo(response)
        elif traceback:
            click.echo(response.json["properties"]["traceback"])
        else:
            _print_job_details(response, verbose=True)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show job progress.")
@click.argument("job_id", type=click.STRING)
@opt_debug
@click.pass_context
def progress(ctx, job_id, debug=False):
    """Show job progress."""
    try:
        _show_progress(ctx, job_id, disable=debug)
    except Exception as e:
        click.echo("Error: %s" % e)


@mhub.command(short_help="Show current jobs.")
@opt_geojson
@click.option(
    "--output_path", "-p",
    type=click.STRING,
    help="Filter jobs by output_path."
)
@click.option(
    "--state", "-s",
    type=click.Choice(
        [
            "todo", "doing", "done", "pending", "progress", "received", "started",
            "success", "failure"
        ]
    ),
    help="Filter jobs by job state."
)
@click.option(
    "--command", "-c",
    type=click.Choice(["execute", "index"]),
    help="Filter jobs by command."
)
@click.option(
    "--queue", "-q",
    type=click.STRING,
    help="Filter jobs by queue."
)
@utils.opt_bounds
@click.option(
    "--since",
    type=click.STRING,
    callback=_get_timestamp,
    help="Filter jobs by timestamp since given time.",
    default="7d"
)
@click.option(
    "--until",
    type=click.STRING,
    callback=_get_timestamp,
    help="Filter jobs by timestamp until given time.",
)
@click.option(
    "--job-name", "-n",
    type=click.STRING,
    help="Filter jobs job name."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Print job details. (Does not work with --geojson.)"
)
@opt_debug
@click.pass_context
def jobs(
    ctx,
    geojson=False,
    since=None,
    until=None,
    verbose=False,
    **kwargs
):
    """Show current jobs."""
    kwargs.update(from_date=since, to_date=until)
    try:
        if geojson:
            click.echo(
                API(**ctx.obj).jobs(geojson=True, **kwargs)
            )
        else:
            # sort by state and then by timestamp
            jobs = list(
                sorted(
                    API(**ctx.obj).jobs(**kwargs).values(),
                    key=lambda x: (
                        x.json["properties"]["state"],
                        x.json["properties"]["timestamp"]
                    )
                )
            )
            if verbose:
                click.echo("%s jobs found. \n" % len(jobs))
            for i in jobs:
                _print_job_details(i, verbose=verbose)
    except Exception as e:
        click.echo("Error: %s" % e)


def _print_job_details(job, verbose=False):
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
    click.echo(click.style("%s" % job.job_id, fg=color, bold=True))

    if verbose:
        # job name
        click.echo("job name: %s" % properties.get("job_name"))

        # state
        click.echo(click.style("state: %s" % job.state))

        # command
        click.echo("command: %s" % properties.get("command"))

        # queue
        click.echo("queue: %s" % properties.get("queue"))

        # output path
        click.echo("output path: %s" % mapchete_config.get("output", {}).get("path"))

        # bounds
        try:
            bounds = ", ".join(map(str, shape(job.json["geometry"]).bounds))
        except:
            bounds = None
        click.echo("bounds: %s" % bounds)

        # parent ID
        click.echo("parent_job_id: %s" % properties.get("parent_job_id"))

        # child ID
        click.echo("child_job_id: %s" % properties.get("child_job_id"))

        # start time
        click.echo(
            "started: %s" % (
                date_to_str(
                    datetime.utcfromtimestamp(properties.get("started")),
                    microseconds=False
                ) if properties.get("started") else None
            )
        )

        # runtime
        runtime = properties.get("runtime")
        click.echo("runtime: %s" % (Timer(runtime) if runtime else None))

        # last received update
        click.echo(
            "last received update: %s" % date_to_str(
                datetime.utcfromtimestamp(properties.get("timestamp")),
                microseconds=False
            )
        )

        # append newline
        click.echo("")


def _show_progress(ctx, job_id, disable=False):
    try:
        with click_spinner.spinner(disable=disable):
            states = API(**ctx.obj).job_progress(job_id)
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
                total=i["progress_data"]["total"],
                disable=disable
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
