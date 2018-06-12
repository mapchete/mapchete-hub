import click
import datetime
import geojson
import json
import requests
from requests.exceptions import ConnectionError
import time
from tqdm import tqdm
import yaml

import mapchete_hub
from mapchete_hub.config import host_options

# https://github.com/tqdm/tqdm/issues/481
tqdm.monitor_interval = 0

job_states = {
    "todo": ["PENDING"],
    "doing": ["PROGRESS", "RECEIVED", "STARTED"],
    "done": ["SUCCESS", "FAILURE"]
}


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
@click.argument('job_id', type=str)
@click.argument('mapchete_file', type=str)
@click.option('--bounds', '-b', type=float, nargs=4)
@click.pass_context
def start(ctx, job_id, mapchete_file, bounds=None):
    start_job(job_id, mapchete_file, bounds)
    get_status(job_id)


@mhub.command(short_help='Stops job.')
@click.argument('job_id', type=str)
@click.pass_context
def stop(ctx):
    click.echo("stop job")


@mhub.command(short_help='Shows job status.')
@click.argument('job_id', type=str)
@click.pass_context
def status(ctx, job_id):
    try:
        get_status(job_id)
    except ConnectionError:
        click.echo("No mapchete hub running under given endpoint.")


@mhub.command(short_help='Shows current jobs.')
@click.option('--geojson', is_flag=True)
@click.pass_context
def jobs(ctx, geojson):
    return get_jobs(as_geojson=geojson)


def start_job(job_id, mapchete_file, bounds):

    def _cleanup_datetime(d):
        """Represent timestamps as strings, not datetime.date objects."""
        return {
            k: _cleanup_datetime(v) if isinstance(v, dict)
            else str(v) if isinstance(v, datetime.date) else v
            for k, v in d.items()
        }

    url = "http://%s:%s/jobs/%s" % (host_options["host_ip"], host_options["port"], job_id)
    data = _cleanup_datetime(
        dict(
            mapchete_config=yaml.safe_load(open(mapchete_file, "r").read()),
            mode="continue",
            zoom=None,
            bounds=bounds,
            point=None,
            wkt_geometry=None,
            tile=None
        )
    )

    try:
        res = requests.post(url, json=data)
    except ConnectionError:
        click.echo("No mapchete hub running under given endpoint.")
        return
    if res.status_code == 409:
        click.echo("job %s already exists" % job_id)
        return
    elif res.status_code == 202:
        res_data = json.loads(res.text)["properties"]
        state = res_data["state"]
        click.echo("job status: %s" % state)
    else:
        raise ValueError("unknown status code: %s", res.status_code)


def get_status(job_id):
    url = "http://%s:%s/jobs/%s" % (host_options["host_ip"], host_options["port"], job_id)
    try:
        res = _get_json(url)
    except ConnectionError as e:
        click.echo("error when getting job %s status: %s" % (job_id, e))
        return

    if res["properties"]["state"] in job_states["todo"]:
        click.echo("waiting for worker to accept job...")
        while True:
            res = _get_json(url)
            if res["properties"]["state"] not in job_states["todo"]:
                break
            time.sleep(1)

    if res["properties"]["state"] in job_states["doing"]:

        def print_verbose_state(state):
            if state == "STARTED":
                msg = "started"
            elif state == "RECEIVED":
                msg = "received"
            elif state == "PROGRESS":
                msg = "in progress"
            else:
                msg = state.lower()
            click.echo("job %s %s" % (job_id, msg))

        current_state = res["properties"]["state"]
        print_verbose_state(current_state)

        while True:
            try:
                res = _get_json(url)
                if res["properties"]["state"] != current_state:
                    current_state = res["properties"]["state"]
                    print_verbose_state(current_state)
                current = res["properties"]["progress_data"]["current"]
                total = res["properties"]["progress_data"]["total"]
                assert isinstance(current, int)
                assert isinstance(total, int)
                break
            except:
                pass
            finally:
                time.sleep(1)

        with tqdm(total=total, initial=current) as pbar:
            while True:
                res = _get_json(url)

                if res["properties"]["state"] in job_states["done"]:
                    break

                elif res["properties"]["state"] == "PROGRESS":
                    last = current

                    if res["properties"]["progress_data"]:
                        current = res["properties"]["progress_data"]["current"]

                        if current and last and current > last:
                            pbar.update(current - last)

                time.sleep(1)

    if res["properties"]["state"] == "SUCCESS":
        click.echo(
            "job %s successfully finished in %ss" % (job_id, res["properties"]["runtime"])
        )

    elif res["properties"]["state"] == "FAILURE":
        click.echo("job %s failed:" % job_id)
        click.echo("traceback:")
        click.echo(res["properties"]["traceback"])

    else:
        raise ValueError("unknown state: %s", res["properties"]["state"])


def get_jobs(as_geojson=False):
    url = "http://%s:%s/jobs" % (host_options["host_ip"], host_options["port"])
    res = _get_json(url)
    if as_geojson:
        click.echo(
            '{\n'
            '  "type": "FeatureCollection",\n'
            '  "features": ['
        )
        features = (i for i in res)
        try:
            feature = next(features)
            while True:
                gj = '    %s' % geojson.Feature(**feature)
                try:
                    feature = next(features)
                    click.echo(gj + ',')
                except StopIteration:
                    click.echo(gj)
                    raise
        except StopIteration:
            pass
        click.echo(
            '  ]\n'
            '}'
        )
    else:
        for feature in res:
            click.echo(
                "%s: %s" % (
                    feature["properties"]["job_id"], feature["properties"]["state"]
                )
            )


def _get_json(url, headers={}):
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        raise ConnectionError("no resource found")
    return json.loads(response.text)
