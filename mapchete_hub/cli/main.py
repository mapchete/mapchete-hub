import click
import json
import requests
from requests.exceptions import ConnectionError
import time
from tqdm import tqdm
import yaml

import mapchete_hub
from mapchete_hub.config import get_host_options

# https://github.com/tqdm/tqdm/issues/481
tqdm.monitor_interval = 0


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
@click.pass_context
def start(ctx, job_id, mapchete_file):
    start_job(job_id, mapchete_file)
    # get_status(job_id)


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
@click.pass_context
def jobs(ctx):
    return get_jobs()


def start_job(job_id, mapchete_file):
    host_opts = get_host_options()
    url = "http://%s:%s/jobs/%s" % (host_opts["host_ip"], host_opts["port"], job_id)
    data = dict(
        mapchete_config=yaml.safe_load(open(mapchete_file, "r").read()),
        mode="continue",
        zoom=None,
        bounds=None,
        wkt_geometry=None,
        point=None,
        tile=None
    )
    res = requests.post(url, json=data)
    assert res.status_code == 200
    click.echo("queued job %s" % job_id)
    # job_status = json.loads(res.text)["status"]
    # if job_status == "QUEUED":
    #     click.echo("job %s registered with current status %s" % (job_id, job_status))
    # elif job_status in ["SUCCESS", "FAILURE"]:
    #     click.echo(
    #         "job %s was already executed earlier with status %s" % (job_id, job_status)
    #     )
    # elif job_status == "PROGRESS":
    #     click.echo("job %s in progress" % job_id)
    # else:
    #     click.echo("job %s unknown status %s " % (job_id, job_status))


def get_status(job_id):
    host_opts = get_host_options()
    url = "http://%s:%s/jobs/%s" % (host_opts["host_ip"], host_opts["port"], job_id)
    res = _get_json(url)
    click.echo(res)

    # if res["status"] == "PENDING":
    #     click.echo("waiting for worker to accept job...")
    #     while True:
    #         res = _get_json(url)
    #         if res["status"] in ["SUCCESS", "FAILURE", "PROGRESS"]:
    #             break
    #         time.sleep(1)
    # if res["status"] == "PROGRESS":
    #     click.echo("job %s in progress" % job_id)
    #     while True:
    #         try:
    #             res = _get_json(url)
    #             current = res["result"]["current"]
    #             total = res["result"]["total"]
    #             assert isinstance(current, int)
    #             assert isinstance(total, int)
    #             break
    #         except:
    #             pass
    #         finally:
    #             time.sleep(1)
    #     with tqdm(total=total, initial=current) as pbar:
    #         while True:
    #             res = _get_json(url)
    #             if res["status"] in ["SUCCESS", "FAILURE"]:
    #                 break
    #             elif res["status"] == "PROGRESS":
    #                 last = current
    #                 if res["result"]:
    #                     current = res["result"]["current"]
    #                     if current and last and current > last:
    #                         pbar.update(current - last)
    #             time.sleep(1)
    # if res["status"] == "SUCCESS":
    #     click.echo("job %s successfully finished" % job_id)
    # if res["status"] == "FAILURE":
    #     click.echo("job %s failed:" % job_id)
    #     click.echo(res["traceback"])
    # if res["status"] == "UNKNOWN":
    #     click.echo("no job named %s currently registered" % job_id)


def get_jobs():
    url = "http://localhost:5555/api/tasks"
    job_baseurl = "http://localhost:5555/api/task/info/"
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, compress'
    }
    res = _get_json(url, headers=headers)
    for job_id, v in res.items():
        click.echo("%s: %s" % (job_id, v["state"]))
        # print(_get_json(job_baseurl + job_id, headers=headers))

    # host_opts = get_host_options()
    # url = "http://%s:%s/jobs" % (host_opts["host_ip"], host_opts["port"])
    # res = _get_json(url)
    # for g in ["unknown", "progress", "success", "failed"]:
    #     click.echo(g + ":")
    #     for j in res[g]:
    #         click.echo(j)
    #     click.echo("\n")


def _get_json(url, headers={}):
    response = requests.get(url, headers=headers)
    # print(response.text)
    return json.loads(response.text)
