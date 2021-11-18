"""
Main REST endpoint.

The API seeks to represent the current status of OGC API Processes: https://github.com/opengeospatial/ogcapi-processes

API:

GET /versions.json
------------------
Show remote package versions.

GET /jobs
---------
Return submitted jobs. Jobs can be filtered by using the following parameters:
    output_path : str
        Filter by output path.
    state : str
        Filter by job state.
    command : str
        Filter by mapchete command.
    job_name : str
        Filter by job name.
    bounds : list or tuple
        Filter by spatial bounds.
    from_date : str
        Filter by earliest date.
    to_date : str
        Filter by latest date.

GET /jobs/{job_id}
------------------
Return job metadata.

DELETE/jobs/{job_id}
--------------------
Cancels a running job.

GET /jobs/{job_id}/results
--------------------------
Return job result.

GET /processes
--------------
Return available processes.

GET /processes/{process_id}
---------------------------
Return detailed information on process.

POST /processes/{process_id}
-------------------------------------
Submit a custom process with a given ID.

POST /processes/{process_id}/execution
-------------------------------------
Trigger a job using a given process_id. This returns a job ID.
"""

import logging
import os
import time
import traceback

from dask.distributed import Client, LocalCluster, get_client
from dask_gateway import Gateway, BasicAuth
from fastapi import Depends, FastAPI, BackgroundTasks, HTTPException, Response
from mapchete import commands, Timer
from mapchete.io import path_is_remote
from mapchete.log import all_mapchete_packages
from mapchete.processes import process_names_docstrings

from mapchete_hub import __version__, models
from mapchete_hub.db import BackendDB
from mapchete_hub.timetools import str_to_date
from mapchete_hub.settings import _get_cluster_specs, DASK_DEFAULT_SPECS, get_dask_specs
from mapchete_hub.slack import send_slack_message


uvicorn_logger = logging.getLogger("uvicorn.access")
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
sh.setFormatter(formatter)

loggers = ["mapchete_hub"]
if os.environ.get("MHUB_ADD_MAPCHETE_LOGGER", "").lower() == "true":  # pragma: no cover
    loggers.extend(list(all_mapchete_packages))
for l in loggers:
    logger = logging.getLogger(l)
    if __name__ != "__main__":
        logger.setLevel(uvicorn_logger.level)
        sh.setLevel(uvicorn_logger.level)
    else:  # pragma: no cover
        logger.setLevel(logging.DEBUG)
        sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)

logger = logging.getLogger(__name__)


MAPCHETE_COMMANDS = {
    "convert": commands.convert,
    "cp": commands.cp,
    "execute": commands.execute,
    "index": commands.index,
}
MHUB_WORKER_EVENT_RATE_LIMIT = float(
    os.environ.get("MHUB_WORKER_EVENT_RATE_LIMIT", 0.2)
)
MHUB_SELF_URL = os.environ.get("MHUB_SELF_URL", "/")


app = FastAPI()

# mhub online message
send_slack_message(
    f"mapchete Hub version {__version__} awaiting orders on {MHUB_SELF_URL}"
)


# dependencies
def get_backend_db():  # pragma: no cover
    url = os.environ.get("MHUB_MONGODB_URL")
    if not url:
        raise ValueError("MHUB_MONGODB_URL must be provided")
    logger.debug("connect to %s", url)
    return BackendDB(src=url)


def get_dask_opts():  # pragma: no cover
    """This allows lazily loading either a LocalCluster, a GatewayCluster or connection to a running scheduler."""
    if os.environ.get("MHUB_DASK_GATEWAY_URL"):  # pragma: no cover
        return {
            "flavor": "gateway",
            "url": os.environ.get("MHUB_DASK_GATEWAY_URL"),
            "gateway_kwargs": {
                "auth": BasicAuth(password=os.environ.get("MHUB_DASK_GATEWAY_PASS"))
            },
            "cluster_kwargs": {
                "minimum": int(os.environ.get("MHUB_DASK_MIN_WORKERS", 10)),
                "maximum": int(os.environ.get("MHUB_DASK_MAX_WORKERS", 1000)),
                "active": os.environ.get("MHUB_DASK_ADAPTIVE_SCALING", "TRUE")
                == "TRUE",
            },
        }
    elif os.environ.get("MHUB_DASK_SCHEDULER_URL"):
        return {"flavor": "scheduler", "url": os.environ.get("MHUB_DASK_SCHEDULER_URL")}
    else:  # pragma: no cover
        logger.warning(
            "Either MHUB_DASK_GATEWAY_URL and MHUB_DASK_GATEWAY_PASS or MHUB_DASK_SCHEDULER_URL have to be set. For now, a local cluster is being used."
        )
        return {"flavor": "local_cluster", "cluster": LocalCluster()}


# REST endpoints


@app.get("/")
def root():
    return {
        "title": f"Mapchete Hub processing server version {__version__}",
        "description": "Example server implementing an adaption of OGC API - Processes",
        "links": [
            {
                "href": "string",
                "rel": "service",
                "type": "application/json",
                "hreflang": "en",
                "title": "string",
            }
        ],
    }


@app.get("/conformance")
def get_conformance():
    raise NotImplementedError()


@app.get("/dask_specs")
def get_dask_specs_presets():
    return DASK_DEFAULT_SPECS


@app.get("/processes")
def get_processes():
    """Lists the processes this API offers."""
    return {
        "processes": [
            {"title": title, "description": description}
            for title, description in process_names_docstrings()
        ]
    }


@app.get("/processes/{process_id}")
def get_process(process_id: str):
    """Returns a detailed description of a process."""
    try:
        title, description = process_names_docstrings(process_id)[0]
        return {"title": title, "description": description}
    except IndexError as exc:
        raise HTTPException(404, f"process '{process_id}' not found") from exc


@app.post("/processes/{process_id}")
def post_process(process_id: str):
    """Returns a detailed description of a process."""
    raise NotImplementedError()


@app.post("/processes/{process_id}/execution", status_code=201)
async def post_job(
    process_id: str,
    job_config: models.MapcheteJob,
    background_tasks: BackgroundTasks,
    backend_db: BackendDB = Depends(get_backend_db),
    dask_opts: dict = Depends(get_dask_opts),
    response: Response = None,
):
    """Executes a process, i.e. creates a new job."""
    try:
        # get dask specs and extract to dictionary
        job_config.params["dask_specs"] = get_dask_specs(
            job_config.params.get("dask_specs", {})
        )

        # create new entry in database
        job = backend_db.new(job_config=job_config)

        # send task to background to be able to quickly return a message
        background_tasks.add_task(
            job_wrapper, job["id"], job_config, backend_db, dask_opts
        )
        response.headers["Location"] = f"/jobs/{job['id']}"

        # return job
        job = backend_db.job(job["id"])
        logger.debug("submitted job %s", job)

        running = len(backend_db.jobs(state="running"))
        logger.debug("currently running %s jobs", running)

        # send message to Slack
        send_slack_message(
            f"job submitted ({running} running)\n" f"{job['properties']['url']}"
        )
        return job
    except Exception as exc:  # pragma: no cover
        logger.exception(exc)
        raise HTTPException(400, str(exc)) from exc


@app.get("/jobs")
def list_jobs(
    output_path: str = None,
    state: str = None,
    command: str = None,
    job_name: str = None,
    bounds: str = None,  # Field(None, example="0.0,1.0,2.0,3.0"),
    from_date: str = None,
    to_date: str = None,
    backend_db: BackendDB = Depends(get_backend_db),
):
    """Returns the running and finished jobs for a process."""
    bounds = tuple(map(float, bounds.split(","))) if bounds else None
    from_date = str_to_date(from_date) if from_date else None
    to_date = str_to_date(to_date) if to_date else None
    kwargs = {
        "output_path": output_path,
        "state": state,
        "command": command,
        "job_name": job_name,
        "bounds": bounds,
        "from_date": from_date,
        "to_date": to_date,
    }
    return {"type": "FeatureCollection", "features": backend_db.jobs(**kwargs)}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the status of a job."""
    try:
        return backend_db.job(job_id)
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Cancel a job execution."""
    try:
        job = backend_db.job(job_id)
        if job["properties"]["state"] in ["pending", "running"]:  # pragma: no cover
            backend_db.set(job_id, state="aborting")
            send_slack_message(f"aborting job {job_id}\n" f"{job['properties']['url']}")
        return backend_db.job(job_id)
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the result of a job."""
    try:
        return backend_db.job(job_id)["properties"]["output_path"]
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


def get_dask_cluster(
    job_id=None,
    flavor=None,
    url=None,
    gateway_kwargs=None,
    cluster=None,
    dask_specs=None,
    **kwargs,
):
    if flavor == "local_cluster" and isinstance(cluster, LocalCluster):
        return cluster
    elif flavor == "gateway":  # pragma: no cover
        gateway = Gateway(url, **gateway_kwargs or {})
        logger.debug("connected to gateway %s", gateway)
        if dask_specs is not None:
            logger.debug("use cluster with %s specs", dask_specs)
            return gateway.new_cluster(
                cluster_options=_get_cluster_specs(gateway, dask_specs=dask_specs)
            )
        else:
            return gateway.new_cluster()
    else:  # pragma: no cover
        raise TypeError("cannot get cluster")


def get_dask_client(flavor=None, url=None, cluster=None):
    if flavor == "local_cluster":
        return Client(cluster)
    elif flavor == "gateway":  # pragma: no cover
        return cluster.get_client()
    elif flavor == "scheduler":  # pragma: no cover
        return get_client(url)
    else:  # pragma: no cover
        raise TypeError("cannot get client")


def job_wrapper(job_id: str, job_config: dict, backend_db: BackendDB, dask_opts: dict):
    """Create a Job iterator through the mapchete_execute function. On every new finished task,
    check whether the task already got the abort status.
    """
    cluster = None
    try:
        # TODO: fix https://github.com/ungarj/mapchete/issues/356
        # before mapchete config validation works again
        # config = job_config.config.dict()
        config = job_config.config
        config["bounds"] = config.get("bounds")
        config["config_dir"] = config.get("config_dir")

        if dask_opts.get("flavor") in ["local_cluster", "gateway"]:
            cluster = get_dask_cluster(
                **dask_opts, dask_specs=job_config.params.get("dask_specs")
            )
            logger.debug("cluster: %s", cluster)
        else:  # pragma: no cover
            logger.debug("no cluster available for flavor %s", dask_opts.get("flavor"))
            cluster = None

        logger.debug("determining dask client")
        dask_client = get_dask_client(
            dask_opts.get("flavor"), url=dask_opts.get("url"), cluster=cluster
        )
        logger.debug("job %s starting mapchete %s", job_id, job_config.command)
        logger.debug("dask dashboard: %s", dask_client.dashboard_link)

        # relative output paths are not useful, so raise exception
        out_path = config.get("output", {}).get("path", {})
        if not path_is_remote(out_path) and not os.path.isabs(
            out_path
        ):  # pragma: no cover
            raise ValueError(f"process output path must be absolute: {out_path}")

        with Timer() as t:
            backend_db.set(
                job_id, state="running", dask_dashboard_link=dask_client.dashboard_link
            )
            send_slack_message(
                f"job started\n"
                f"{dask_client.dashboard_link}\n"
                f"{os.path.join(MHUB_SELF_URL, 'jobs', job_id)}"
            )

            # Mapchete now will initialize the process and prepare all the tasks required.
            job = MAPCHETE_COMMANDS[job_config.command](
                config,
                **{
                    k: v
                    for k, v in job_config.params.items()
                    if k not in ["job_name", "dask_specs"]
                },
                as_iterator=True,
                concurrency="dask",
                dask_client=dask_client,
            )
            # override the MHUB_DASK_MIN_WORKERS and MHUB_DASK_MAX_WORKERS default settings
            # if it makes sense to avoid asking for more workers than could be possible used
            # this can be refined once we expose a more detailed information on the types of
            # job tasks: https://github.com/ungarj/mapchete/issues/383
            if cluster is not None and dask_opts.get("flavor") in [
                "local_cluster",
                "gateway",
            ]:  # pragma: no cover
                cluster_kwargs = dask_opts.get("cluster_kwargs")
                if cluster_kwargs:
                    adapted_kwargs = dict(
                        cluster_kwargs,
                        # the minimum should not be larger than the expected number of job tasks
                        minimum=min(
                            [cluster_kwargs.get("minimum", 10), job.tiles_tasks]
                        ),
                        # the maximum should also not be larger than the expected number of job tasks
                        maximum=min(
                            [
                                cluster_kwargs.get("maximum", 1000),
                                max([job.preprocessing_tasks, job.tiles_tasks]),
                            ]
                        ),
                    )
                    logger.debug("adapt cluster: %s", adapted_kwargs)
                    cluster.adapt(**adapted_kwargs)
            backend_db.set(job_id, current_progress=0, total_progress=len(job))
            logger.debug("job %s created", job_id)
            # By iterating through the Job object, mapchete will send all tasks to the dask cluster and
            # yield the results.
            last_event = 0.0
            for i, _ in enumerate(job, 1):
                event_time_passed = time.time() - last_event
                if event_time_passed > MHUB_WORKER_EVENT_RATE_LIMIT or i == len(job):
                    last_event = time.time()
                    # determine if there is a cancel signal for this task
                    backend_db.set(job_id, current_progress=i)
                    logger.debug(
                        "job %s %s tasks from %s finished", job_id, i, len(job)
                    )
                    state = backend_db.job(job_id)["properties"]["state"]
                    if state == "aborting":  # pragma: no cover
                        logger.debug("job %s abort state caught: %s", job_id, state)
                        # By calling the job's cancel method, all pending futures will be cancelled.
                        job.cancel()
                        backend_db.set(job_id, state="cancelled")
                        send_slack_message(
                            "cancelled job\n"
                            f"{os.path.join(MHUB_SELF_URL, 'jobs', job_id)}"
                        )
                        return
        # job finished successfully
        backend_db.set(job_id, state="done")
        logger.debug("job %s finished in %s", job_id, t)
        send_slack_message(
            f"job finished in {t}\n" f"{os.path.join(MHUB_SELF_URL, 'jobs', job_id)}"
        )

    except Exception as exc:
        backend_db.set(
            job_id=job_id,
            state="failed",
            exception=repr(exc),
            traceback="".join(traceback.format_tb(exc.__traceback__)),
        )
        logger.exception(exc)
        send_slack_message(
            f"job failed with {exc}\n"
            f"{''.join(traceback.format_tb(exc.__traceback__))}\n"
            f"{os.path.join(MHUB_SELF_URL, 'jobs', job_id)}"
        )
    finally:  # pragma: no cover
        try:
            if cluster:
                logger.debug("try to shutdown cluster %s", cluster)
                cluster.shutdown()
        except Exception as exc:
            logger.error("cluster shutdown threw exception %s", exc)
