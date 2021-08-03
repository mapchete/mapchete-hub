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

from dask.distributed import as_completed, Client
import datetime
from fastapi import Depends, FastAPI, BackgroundTasks, HTTPException, Response
import logging
from mapchete import commands
import os
from typing import Union

from mapchete_hub import __version__, models
from mapchete_hub.db import BackendDB


uvicorn_logger = logging.getLogger("uvicorn.access")
logger = logging.getLogger("mapchete_hub")
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
sh.setFormatter(formatter)
if __name__ != "__main__":
    logger.setLevel(uvicorn_logger.level)
    sh.setLevel(uvicorn_logger.level)
else:
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
    # if scheduler is None:
    #     raise ValueError("DASK_SCHEDULER environment variable must be set")
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
        logger.debug(f"currently running {len(backend_db.jobs())} jobs")
        return job
    except Exception as e:
        logger.exception(e)
        raise
 

@app.get("/jobs")
def list_jobs(
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
    return backend_db.jobs(
        output_path=output_path,
        state=state,
        command=command,
        job_name=job_name,
        bounds=bounds,
        from_date=from_date,
        to_date=to_date,
    )


@app.get("/jobs/{job_id}")
def get_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Returns the status of a job."""
    return backend_db.job(job_id)


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str, backend_db: BackendDB = Depends(get_backend_db)):
    """Cancel a job execution."""
    backend_db.set(job_id, state="aborting")
    return backend_db.job(job_id)


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    """Returns the result of a job."""
    return backend_db.job(job_id)["result"]


def job_wrapper(
    job_id: str,
    job_config: dict,
    backend_db: BackendDB,
    dask_scheduler: str
):
    """ Create a Job iterator through the mapchete_execute function. On every new finished task,
        check whether the task already got the abort status.
    """
    logger.debug(f"starting mapchete {job_config.command}")
    try:
        backend_db.set(job_id, state="running")
        # Mapchete now will initialize the process and prepare all the tasks required.
        job = MAPCHETE_COMMANDS[job_config.command](
            job_config.config.dict(),
            **job_config.params,
            as_iterator=True,
            concurrency="dask",
            dask_scheduler=dask_scheduler
        )
        backend_db.set(job_id, current_progress=0, total_progress=len(job))
        logger.debug(f"created {job_id}")
        # By iterating through the Job object, mapchete will send all tasks to the dask cluster and
        # yield the results.
        for i, t in enumerate(job):
            logger.debug(f"job {job_id} task {i + 1}/{len(job)} finished")
            # determine if there is a cancel signal for this task
            backend_db.set(job_id, current_progress=i + 1)
            state = backend_db.job(job_id)["properties"]["state"]
            if state == "aborting":
                logger.debug(f"abort state caught: {state}")
                # By calling the job's cancel method, all pending futures will be cancelled.
                job.cancel()
                backend_db.set(job_id, state="cancelled")
                return
        # job finished successfully
        backend_db.set(job_id, state="done")
    except Exception as e:
        backend_db.set(job_id=job_id, state="failed", exception=e)
        logger.exception(e)
