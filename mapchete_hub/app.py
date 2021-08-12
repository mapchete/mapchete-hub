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

from dask.distributed import Client, get_client
import datetime
from fastapi import Depends, FastAPI, BackgroundTasks, HTTPException, Response
import logging
from mapchete import commands
from mapchete.processes import process_names_docstrings, registered_processes
import os
from pydantic import Field
import time
import traceback
from typing import Union

from mapchete_hub import __version__, models
from mapchete_hub.db import BackendDB
from mapchete_hub.timetools import str_to_date


uvicorn_logger = logging.getLogger("uvicorn.access")
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
sh.setFormatter(formatter)

loggers = ["mapchete_hub"]
if os.environ.get("MHUB_ADD_MAPCHETE_LOGGER", "").lower() == "true":  # pragma: no cover
    loggers.append("mapchete")
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
MHUB_WORKER_EVENT_RATE_LIMIT = os.environ.get("MHUB_WORKER_EVENT_RATE_LIMIT", 0.2)


app = FastAPI()

# dependencies

def get_backend_db():  # pragma: no cover
    url = os.environ.get("MHUB_MONGODB_URL")
    if not url:
        raise ValueError("MHUB_MONGODB_URL must be provided")
    logger.debug(f"connect to {url}")
    return BackendDB(src=url)


def get_dask_scheduler():  # pragma: no cover
    scheduler = os.environ.get("MHUB_DASK_SCHEDULER_URL")
    if scheduler is None:
        raise ValueError("DASK_SCHEDULER environment variable must be set")
    return scheduler


# REST endpoints

@app.get("/")
def root():
    return {
        "title": f"Mapchete Hub processing server version {__version__}",
        "description": "Example server implementing the OGC API - Processes 1.0",
        "links": [
            {
                "href": "string",
                "rel": "service",
                "type": "application/json",
                "hreflang": "en",
                "title": "string"
            }
        ]
}


@app.get("/conformance")
def get_conformance():
    raise NotImplementedError()


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
    except IndexError:
        raise HTTPException(404, f"process '{process_id}' not found")


@app.post("/processes/{process_id}")
def post_process(process_id: str):
    """Returns a detailed description of a process."""
    raise NotImplementedError()


@app.post("/processes/{process_id}/execution", status_code=201)
def post_job(
    process_id: str,
    job_config: models.MapcheteJob,
    background_tasks: BackgroundTasks,
    backend_db: BackendDB = Depends(get_backend_db),
    dask_scheduler: str = Depends(get_dask_scheduler),
    response: Response = None
):
    """Executes a process, i.e. creates a new job."""
    try:
        job = backend_db.new(job_config=job_config)
        # send task to background to be able to quickly return a message
        background_tasks.add_task(
            job_wrapper,
            job["id"],
            job_config,
            backend_db,
            dask_scheduler
        )
        response.headers["Location"] = f"/jobs/{job['id']}"
        # return job
        job = backend_db.job(job["id"])
        logger.debug(f"submitted job {job}")
        logger.debug(f"currently running {len(backend_db.jobs(state='running'))} jobs")
        return job
    except Exception as e:  # pragma: no cover
        logger.exception(e)
        raise HTTPException(400, str(e))
 

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
    return backend_db.jobs(**kwargs)


@app.get("/jobs/{job_id}")
def get_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the status of a job."""
    try:
        return backend_db.job(job_id)
    except KeyError as e:
        raise HTTPException(404, f"job {job_id} not found in the database")


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Cancel a job execution."""
    try:
        job = backend_db.job(job_id)
        if job["properties"]["state"] in ["pending", "running"]:  # pragma: no cover
            backend_db.set(job_id, state="aborting")
        return backend_db.job(job_id)
    except KeyError as e:
        raise HTTPException(404, f"job {job_id} not found in the database")


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the result of a job."""
    try:
        return backend_db.job(job_id)["properties"]["output_path"]
    except KeyError as e:
        raise HTTPException(404, f"job {job_id} not found in the database")


def job_wrapper(
    job_id: str,
    job_config: dict,
    backend_db: BackendDB,
    dask_scheduler: str
):
    """ Create a Job iterator through the mapchete_execute function. On every new finished task,
        check whether the task already got the abort status.
    """
    logger.debug(f"job {job_id} starting mapchete {job_config.command}")
    try:
        config = job_config.config.dict()

        # relative output paths are not useful, so raise exception
        out_path = config.get("output", {}).get("path", {})
        if not os.path.isabs(out_path):
            raise ValueError(f"process output path must be absolute: {out_path}")

        backend_db.set(job_id, state="running")

        # Mapchete now will initialize the process and prepare all the tasks required.
        job = MAPCHETE_COMMANDS[job_config.command](
            config,
            **{k: v for k, v in job_config.params.items() if k != "job_name"},
            as_iterator=True,
            concurrency="dask",
            dask_client=get_client(dask_scheduler) if dask_scheduler else Client()
        )
        backend_db.set(job_id, current_progress=0, total_progress=len(job))
        logger.debug(f"job {job_id} created")
        # By iterating through the Job object, mapchete will send all tasks to the dask cluster and
        # yield the results.
        last_event = 0.
        for i, t in enumerate(job):
            i += 1
            logger.debug(f"job {job_id} task {i}/{len(job)} finished")

            event_time_passed = time.time() - last_event
            if event_time_passed > MHUB_WORKER_EVENT_RATE_LIMIT or i == len(job):
                last_event = time.time()
                # determine if there is a cancel signal for this task
                backend_db.set(job_id, current_progress=i)
                state = backend_db.job(job_id)["properties"]["state"]
                if state == "aborting":  # pragma: no cover
                    logger.debug(f"job {job_id} abort state caught: {state}")
                    # By calling the job's cancel method, all pending futures will be cancelled.
                    job.cancel()
                    backend_db.set(job_id, state="cancelled")
                    return
        # job finished successfully
        backend_db.set(job_id, state="done")
    except Exception as e:
        backend_db.set(job_id=job_id, state="failed", exception=repr(e), traceback="".join(traceback.format_tb(e.__traceback__)))
        logger.exception(e)
