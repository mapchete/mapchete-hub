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

import asyncio
from dask.distributed import as_completed, Client
import datetime
from fastapi import Depends, FastAPI, BackgroundTasks
import logging
from mapchete import commands
import os
from random import random
import time
from typing import Union
from uuid import uuid4

from mapchete_hub import __version__
from mapchete_hub.db import BackendDB


uvicorn_logger = logging.getLogger("uvicorn.access")
logger = logging.getLogger("mapchete_hub")
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
sh.setFormatter(formatter)
if __name__ != "main":
    logger.setLevel(uvicorn_logger.level)
    sh.setLevel(uvicorn_logger.level)
else:
    logger.setLevel(logging.DEBUG)
    sh.setLevel(logging.DEBUG)
logger.addHandler(sh)
logger = logging.getLogger(__name__)


app = FastAPI()

# dependencies

def get_backend_db():
    url = os.environ.get("MONGO_URL")
    if not url:
        raise ValueError("MONGO_URL must be provided")
    logger.debug(f"connect to {url}")
    return BackendDB(src=url)


def get_dask_scheduler():
    scheduler = os.environ.get("DASK_SCHEDULER")
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
    raise NotImplementedError()


@app.post("/processes/{process_id}")
def post_process(process_id: str):
    """Returns a detailed description of a process."""
    raise NotImplementedError()


@app.post("/processes/{process_id}/execution")
def post_job(
    background_tasks: BackgroundTasks,
    process_id: str,
    backend_db: BackendDB = Depends(get_backend_db),
    dask_scheduler: str = Depends(get_dask_scheduler)
):
    """Executes a process, i.e. creates a new job."""
    job_id = uuid4().hex
    # send task to background to be able to quickly return a message
    background_tasks.add_task(task_wrapper, job_id, backend_db, dask_scheduler)
    return {"job_id": job_id}


@app.get("/jobs")
async def list_jobs(
    backend_db: BackendDB = Depends(get_backend_db),
    output_path: str = None,
    state: str = None,
    command: str = None,
    job_name: str = None,
    bounds: Union[list, tuple] = None,
    from_date: datetime.datetime = None,
    to_date: datetime.datetime = None,
):
    """Returns the running and finished jobs for a process."""
    logger.debug(f"using {backend_db}")
    result = backend_db.jobs()
    logger.debug(result)
    return result


@app.get("/jobs/{job_id}")
async def get_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the status of a job."""
    return backend_db.job(job_id)


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Cancel a job execution."""
    backend_db.set(job_id, status="abort")
    # async with redis.client() as conn:
    #     status = await conn.get(f"status-{job_id}")
    #     if status == "started":
    #         await cancel_task(conn, job_id)
    #     status = await conn.get(f"status-{job_id}")
    return {"job_id": job_id, "status": status or "unknown"}


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    """Returns the result of a job."""
    raise NotImplementedError()


async def cancel_task(backend_db: BackendDB, job_id: str):
    """ Send a task cancellation message. Does not check if the task is
        actually valid.
    """
    logger.info(f"cancel job {job_id}")
    # return await conn.lpush(f"cancel-{job_id}", "cancel")
    return await conn.set(f"status-{job_id}", "abort")


async def task_wrapper(job_id: str, backend_db: BackendDB, dask_scheduler: str):
    """ Create a Job iterator through the mapchete_execute function. On every new finished task,
        check whether the task already got the abort status.
    """
    logger.info(f"Starting task {job_id}")
    logger.debug("starting mapchete_execute")
    await conn.set(f"status-{job_id}", "started")
    # Mapchete now will initialize the process and prepare all the tasks required.
    job = mapchete_execute(
        None,
        as_iterator=True,
        concurrency="dask",
        executor_kwargs=dict(dask_scheduler=dask_scheduler)
    )
    logger.debug(f"created {job}")
    # By iterating through the Job object, mapchete will send all tasks to the dask cluster and
    # yield the results.
    for i, t in enumerate(job):
        logger.debug(f"job {job_id} task {i + 1}/{len(job)} finished")
        # determine if there is a cancel signal for this task
        status = await conn.get(f"status-{job_id}")
        if status == "abort":
            logger.debug(f"abort status caught: {status}")
            # By calling the job's cancel method, all pending futures will be cancelled.
            job.cancel()
            await conn.set(f"status-{job_id}", "cancelled")
            return
        # TODO update job state
    # task finished successfully
    conn.set(f"status-{job_id}", "finished")
