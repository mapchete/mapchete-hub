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

from contextlib import contextmanager
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
from mapchete_hub.settings import (
    get_gateway_cluster_options,
    DASK_DEFAULT_SPECS,
    get_dask_specs,
)
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
MHUB_SELF_INSTANCE_NAME = os.environ.get("MHUB_SELF_INSTANCE_NAME", "mapchete Hub")


app = FastAPI()

CACHE = {}

# mhub online message
send_slack_message(
    f"*{MHUB_SELF_INSTANCE_NAME} version {__version__} awaiting orders on* {MHUB_SELF_URL}"
)


# dependencies
def get_backend_db():  # pragma: no cover
    url = os.environ.get("MHUB_MONGODB_URL")
    if not url:
        raise ValueError("MHUB_MONGODB_URL must be provided")
    if "backendb" not in CACHE:
        logger.debug("connect to %s", url)
        CACHE["backendb"] = BackendDB(src=url)
    return CACHE["backendb"]


def get_dask_cluster_setup():  # pragma: no cover
    """This allows lazily loading either a LocalCluster, a GatewayCluster or connection to a running scheduler."""
    if os.environ.get("MHUB_DASK_GATEWAY_URL"):  # pragma: no cover
        return {
            "flavor": "gateway",
            "url": os.environ.get("MHUB_DASK_GATEWAY_URL"),
            "gateway_kwargs": {
                "auth": BasicAuth(password=os.environ.get("MHUB_DASK_GATEWAY_PASS"))
            },
        }
    elif os.environ.get("MHUB_DASK_SCHEDULER_URL"):
        return {"flavor": "scheduler", "url": os.environ.get("MHUB_DASK_SCHEDULER_URL")}
    else:  # pragma: no cover
        logger.warning(
            "Either MHUB_DASK_GATEWAY_URL and MHUB_DASK_GATEWAY_PASS or MHUB_DASK_SCHEDULER_URL have to be set. For now, a local cluster is being used."
        )
        if "cluster" in CACHE:
            logger.debug("using cached LocalCluster")
        else:
            logger.debug("creating LocalCluster")
            CACHE["cluster"] = LocalCluster(processes=False)
        return {"flavor": "local_cluster", "cluster": CACHE["cluster"]}


# REST endpoints


@app.get("/")
async def root():
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
async def get_conformance():
    raise NotImplementedError()


@app.get("/dask_specs")
async def get_dask_specs_presets():
    return DASK_DEFAULT_SPECS


@app.get("/processes")
async def get_processes():
    """Lists the processes this API offers."""
    return {
        "processes": [
            {"title": title, "description": description}
            for title, description in process_names_docstrings()
        ]
    }


@app.get("/processes/{process_id}")
async def get_process(process_id: str):
    """Returns a detailed description of a process."""
    try:
        title, description = process_names_docstrings(process_id)[0]
        return {"title": title, "description": description}
    except IndexError as exc:
        raise HTTPException(404, f"process '{process_id}' not found") from exc


@app.post("/processes/{process_id}")
async def post_process(process_id: str):
    """Returns a detailed description of a process."""
    raise NotImplementedError()


@app.post("/processes/{process_id}/execution", status_code=201)
async def post_job(
    process_id: str,
    job_config: models.MapcheteJob,
    background_tasks: BackgroundTasks,
    backend_db: BackendDB = Depends(get_backend_db),
    dask_cluster_setup: dict = Depends(get_dask_cluster_setup),
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
            job_wrapper, job["id"], job_config, backend_db, dask_cluster_setup
        )
        response.headers["Location"] = f"/jobs/{job['id']}"

        # return job
        job = backend_db.job(job["id"])
        logger.debug("submitted job %s", job)

        running = len(backend_db.jobs(state="running"))
        logger.debug("currently running %s jobs", running)

        # send message to Slack
        send_slack_message(
            f"*{MHUB_SELF_INSTANCE_NAME}: job '{job['properties']['job_name']}' with ID {job['id']} submitted ({running} running)*\n"
            f"{job['properties']['url']}"
        )
        return job
    except Exception as exc:  # pragma: no cover
        logger.exception(exc)
        raise HTTPException(400, str(exc)) from exc


@app.get("/jobs")
async def list_jobs(
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
async def get_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the status of a job."""
    try:
        return backend_db.job(job_id)
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Cancel a job execution."""
    try:
        job = backend_db.job(job_id)
        if job["properties"]["state"] in ["pending", "running"]:  # pragma: no cover
            backend_db.set(job_id, state="aborting")
            send_slack_message(
                f"*{MHUB_SELF_INSTANCE_NAME}: aborting {job['properties']['job_name']}*\n"
                f"{job['properties']['url']}"
            )
        return backend_db.job(job_id)
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """
    Return the results of a job.

    status code    content     condition
    404            -           Job ID not found.
    200            JSON        Job done.
    404            -           Job pending or running.
    400            JSON        Job aborting or failed.

    Exceptions (http://schemas.opengis.net/ogcapi/processes/part1/1.0/openapi/schemas/exception.yaml):
        title: Exception Schema
        description: JSON schema for exceptions based on RFC 7807
        type: object
        required:
        - type
        properties:
        type:
            type: string
        title:
            type: string
        status:
            type: integer
        detail:
            type: string
        instance:
            type: string
        additionalProperties: true
    """
    # raise if Job ID not found
    try:
        job = backend_db.job(job_id)
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc

    if job["properties"]["state"] == "done":
        return job["properties"]["results"]

    elif job["properties"]["state"] in ["pending", "running"]:
        raise HTTPException(404, f"job {job_id} does not yet have a result")

    elif job["properties"]["state"] in ["aborting", "cancelled"]:
        raise HTTPException(
            400,
            {
                "properties": {
                    "type": "Cancelled",
                    "detail": "Job aborted due to user request.",
                }
            },
        )

    elif job["properties"]["state"] == "failed":
        raise HTTPException(
            400,
            {
                "properties": {
                    "type": job["properties"]["exception"],
                    "detail": job["properties"]["traceback"],
                }
            },
        )
    else:
        raise ValueError("invalid job state")


@contextmanager
def dask_cluster(
    job_id=None,
    flavor=None,
    url=None,
    gateway_kwargs=None,
    cluster=None,
    dask_specs=None,
    **kwargs,
):
    if flavor == "local_cluster" and isinstance(cluster, LocalCluster):
        logger.info("use existing %s", cluster)
        yield cluster
    elif flavor == "gateway":  # pragma: no cover
        gateway = Gateway(url, **gateway_kwargs or {})
        logger.debug("connected to gateway %s", gateway)
        if dask_specs is not None:
            logger.info("use gateway cluster with %s specs", dask_specs)
            with gateway.new_cluster(
                cluster_options=get_gateway_cluster_options(
                    gateway, dask_specs=dask_specs
                )
            ) as cluster:
                yield cluster
                logger.info("closing cluster %s", cluster)
            logger.info("closed cluster %s", cluster)
        else:
            logger.info("use gateway cluster with default specs")
            with gateway.new_cluster() as cluster:
                yield cluster
                logger.info("closing cluster %s", cluster)
            logger.info("closed cluster %s", cluster)
    elif flavor == "scheduler":  # pragma: no cover
        logger.info("cluster exists, connecting directly to scheduler")
        yield None
    else:  # pragma: no cover
        raise TypeError("cannot get cluster")


@contextmanager
def dask_client(dask_cluster_setup=None, cluster=None):
    flavor = dask_cluster_setup.get("flavor")
    if flavor == "local_cluster":
        with Client(cluster, set_as_default=False) as client:
            logger.info("started client %s", client)
            yield client
            logger.info("closing client %s", client)
        logger.info("closed client %s", client)
    elif flavor == "gateway":  # pragma: no cover
        with cluster.get_client(set_as_default=False) as client:
            logger.info("started client %s", client)
            yield client
            logger.info("closing client %s", client)
        logger.info("closed client %s", client)
    elif flavor == "scheduler":  # pragma: no cover
        url = dask_cluster_setup.get("url")
        logger.info("connect to scheduler %s", url)
        yield get_client(url)
        logger.info("no client to close")
        # NOTE: we don't close the client afterwards as it would affect other jobs using the same client
    else:  # pragma: no cover
        raise TypeError("cannot get client")


def cluster_adapt(cluster, flavor=None, adapt_options=None):
    if cluster is None:  # pragma: no cover
        logger.debug("cluster does not support adaption")
    elif flavor == "local_cluster":  # pragma: no cover
        cluster.adapt(**{k: v for k, v in adapt_options.items() if k not in ["active"]})
    elif flavor == "gateway":  # pragma: no cover
        logger.debug("adapt cluster: %s", adapt_options)
        cluster.adapt(**adapt_options)
    else:
        raise TypeError(f"cannot determine cluster type: {cluster}")


def job_wrapper(
    job_id: str, job_config: dict, backend_db: BackendDB, dask_cluster_setup: dict
):
    """Create a Job iterator through the mapchete_execute function. On every new finished task,
    check whether the task already got the abort status.
    """
    try:
        logger.info("start fastAPI background task with job %s", job_id)
        job_meta = backend_db.set(job_id, state="running")

        # TODO: fix https://github.com/ungarj/mapchete/issues/356
        # before mapchete config validation works again
        # config = job_config.config.dict()
        config = job_config.config
        config["bounds"] = config.get("bounds")
        config["config_dir"] = config.get("config_dir")

        dask_specs = job_config.params.get("dask_specs")

        # relative output paths are not useful, so raise exception
        out_path = config.get("output", {}).get("path", {})
        if not path_is_remote(out_path) and not os.path.isabs(
            out_path
        ):  # pragma: no cover
            raise ValueError(f"process output path must be absolute: {out_path}")

        # Mapchete now will initialize the process and prepare all the tasks required.
        logger.info("initializing job %s with mapchete %s", job_id, job_config.command)
        with Timer() as timer_initialize:
            job = MAPCHETE_COMMANDS[job_config.command](
                config,
                **{
                    k: v
                    for k, v in job_config.params.items()
                    if k not in ["job_name", "dask_specs"]
                },
                as_iterator=True,
                concurrency="dask",
            )
        backend_db.set(job_id, current_progress=0, total_progress=len(job))
        logger.info("job %s initialized in %s", job_id, timer_initialize)

        logger.info("requesting dask cluster and dask client...")
        with dask_cluster(**dask_cluster_setup, dask_specs=dask_specs) as cluster:
            logger.info("job %s cluster: %s", job_id, cluster)
            with dask_client(
                dask_cluster_setup=dask_cluster_setup, cluster=cluster
            ) as client:
                logger.info("job %s client: %s", job_id, client)

                logger.debug("set %s as job executor", client)
                job.set_executor_kwargs(dict(dask_client=client))
                logger.debug("dask dashboard: %s", client.dashboard_link)

                with Timer() as timer_job:
                    job_meta = backend_db.set(
                        job_id,
                        dask_dashboard_link=client.dashboard_link,
                    )
                    send_slack_message(
                        f"*{MHUB_SELF_INSTANCE_NAME}: {job_meta['properties']['job_name']} started*\n"
                        f"{client.dashboard_link}\n"
                        f"{job_meta['properties']['url']}"
                    )
                    # override the MHUB_DASK_MIN_WORKERS and MHUB_DASK_MAX_WORKERS default settings
                    # if it makes sense to avoid asking for more workers than could be possible used
                    # this can be refined once we expose a more detailed information on the types of
                    # job tasks: https://github.com/ungarj/mapchete/issues/383
                    adapt_options = dask_specs.get("adapt_options")
                    if adapt_options:
                        logger.debug("default adapt options: %s", adapt_options)
                        if job_config.params.get("dask_compute_graph", True):
                            # the minimum should not be larger than the expected number of job tasks
                            min_workers = min(
                                [adapt_options["minimum"], job.tiles_tasks]
                            )
                            # the maximum should also not be larger than one eigth of the expected number of tasks
                            max_workers = min([adapt_options["maximum"], len(job) // 8])
                        else:
                            # the minimum should not be larger than the expected number of job tasks
                            min_workers = min(
                                [adapt_options["minimum"], job.tiles_tasks]
                            )
                            # the maximum should also not be larger than the expected number of job tasks
                            max_workers = min(
                                [
                                    adapt_options["maximum"],
                                    max([job.preprocessing_tasks, job.tiles_tasks]),
                                ]
                            )
                        if max_workers < min_workers:
                            max_workers = min_workers
                        adapt_options.update(
                            minimum=min_workers,
                            maximum=max_workers,
                        )
                    logger.debug("set cluster adapt to %s", adapt_options)
                    cluster_adapt(
                        cluster,
                        flavor=dask_cluster_setup.get("flavor"),
                        adapt_options=adapt_options,
                    )

                    # By iterating through the Job object, mapchete will send all tasks to the dask cluster and
                    # yield the results.
                    last_event = 0.0
                    for i, _ in enumerate(job, 1):
                        event_time_passed = time.time() - last_event
                        if (
                            event_time_passed > MHUB_WORKER_EVENT_RATE_LIMIT
                            or i == len(job)
                        ):
                            last_event = time.time()
                            # determine if there is a cancel signal for this task
                            backend_db.set(job_id, current_progress=i)
                            logger.debug(
                                "job %s %s tasks from %s finished", job_id, i, len(job)
                            )
                            state = backend_db.job(job_id)["properties"]["state"]
                            if state == "aborting":  # pragma: no cover
                                logger.info(
                                    "job %s abort state caught: %s", job_id, state
                                )
                                # By calling the job's cancel method, all pending futures will be cancelled.
                                try:
                                    job.cancel()
                                except Exception:
                                    # catching possible Exceptions (due to losing scheduler before all futures are
                                    # cancelled, etc.) makes sure, the job gets the correct cancelled state
                                    pass
                                backend_db.set(job_id, state="cancelled")
                                send_slack_message(
                                    f"*{MHUB_SELF_INSTANCE_NAME}: {job_meta['properties']['job_name']} cancelled*\n"
                                    f"{job_meta['properties']['url']}"
                                )
                                break
                    else:
                        # job finished successfully
                        backend_db.set(
                            job_id,
                            state="done",
                            results={
                                "imagesOutput": {
                                    "href": job.stac_item_path,
                                    "type": "application/json",
                                }
                            },
                        )
                        logger.info("job %s finished in %s", job_id, timer_job)
                        send_slack_message(
                            f"*{MHUB_SELF_INSTANCE_NAME}: {job_meta['properties']['job_name']} finished in {timer_job}*\n"
                            f"{job_meta['properties']['url']}"
                        )

    except Exception as exc:
        logger.info("job %s raised an Exception: %s", job_id, exc)
        job_meta = backend_db.set(
            job_id=job_id,
            state="failed",
            exception=repr(exc),
            traceback="".join(traceback.format_tb(exc.__traceback__)),
        )
        logger.exception(exc)
        send_slack_message(
            f"*{MHUB_SELF_INSTANCE_NAME}: {job_meta['properties']['job_name']} failed*\n"
            f"{exc}\n"
            f"{''.join(traceback.format_tb(exc.__traceback__))}\n"
            f"{job_meta['properties']['url']}"
        )
    finally:
        logger.info("end fastAPI background task with job %s", job_id)
