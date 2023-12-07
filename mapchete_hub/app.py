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
    status : str
        Filter by job status.
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
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from mapchete.config.models import DaskSettings
from mapchete.enums import Status
from mapchete.log import all_mapchete_packages
from mapchete.processes import process_names_docstrings

from mapchete_hub import __version__
from mapchete_hub.cluster import get_dask_cluster_setup
from mapchete_hub.db import BaseStatusHandler, init_backenddb
from mapchete_hub.job_wrapper import job_wrapper
from mapchete_hub.models import MapcheteJob
from mapchete_hub.settings import DASK_DEFAULT_SPECS, get_dask_specs, mhub_settings
from mapchete_hub.slack import send_slack_message
from mapchete_hub.timetools import str_to_date

uvicorn_logger = logging.getLogger("uvicorn.access")
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
sh.setFormatter(formatter)

loggers = ["mapchete_hub"]
if mhub_settings.add_mapchete_logger:  # pragma: no cover
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


app = FastAPI()

CACHE = dict()

# mhub online message
send_slack_message(
    f"*{mhub_settings.self_instance_name} version {__version__} awaiting orders on* {mhub_settings.self_url}"
)


# dependencies
def get_backend_db() -> BaseStatusHandler:  # pragma: no cover
    if "backend_db" not in CACHE:
        logger.debug("no backend db found in cache, creating...")
        if mhub_settings.backend_db == "memory":
            logger.warning(
                "MHUB_MONGODB_URL not provided; using in-memory metadata store"
            )
        CACHE["backend_db"] = init_backenddb(src=mhub_settings.backend_db)
    return CACHE["backend_db"]


# REST endpoints
@app.get("/")
async def root() -> dict:
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
async def get_dask_specs_presets() -> dict:
    return DASK_DEFAULT_SPECS


@app.get("/processes")
async def get_processes() -> dict:
    """Lists the processes this API offers."""
    return {
        "processes": [
            {"title": title, "description": description}
            for title, description in process_names_docstrings()
        ]
    }


@app.get("/processes/{process_id}")
async def get_process(process_id: str) -> dict:
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
    job_config: MapcheteJob,
    background_tasks: BackgroundTasks,
    backend_db: BaseStatusHandler = Depends(get_backend_db),
    dask_cluster_setup: dict = Depends(get_dask_cluster_setup),
    response: Response = None,
) -> dict:
    """Executes a process, i.e. creates a new job."""
    try:
        # get dask specs and settings
        job_config.params["dask_specs"] = get_dask_specs(
            job_config.params.get("dask_specs", "default")
        )
        job_config.params["dask_settings"] = DaskSettings(
            **job_config.params.pop("dask_settings")
            if "dask_settings" in job_config.params
            else {}
        )

        # create new entry in database
        job = backend_db.new(job_config=job_config)
        # send task to background to be able to quickly return a message
        background_tasks.add_task(
            job_wrapper,
            job,
            job_config,
            backend_db,
            dask_cluster_setup,
        )
        response.headers["Location"] = f"/jobs/{job.job_id}"

        # return job
        job = backend_db.job(job.job_id)
        logger.debug("submitted job %s", job)

        running = len(backend_db.jobs(status=Status.running))
        logger.debug("currently running %s jobs", running)

        # send message to Slack
        send_slack_message(
            f"*{mhub_settings.self_instance_name}: job '<{job.url}|{job.job_name}>' with ID {job.job_id} submitted ({running} running)*\n"
        )
        return job.to_geojson_dict()
    except Exception as exc:  # pragma: no cover
        logger.exception(exc)
        raise HTTPException(400, str(exc)) from exc


@app.get("/jobs")
async def list_jobs(
    output_path: Optional[str] = None,
    status: Optional[str] = None,
    command: Optional[str] = None,
    job_name: Optional[str] = None,
    bounds: Optional[str] = None,  # Field(None, example="0.0,1.0,2.0,3.0"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    backend_db: BaseStatusHandler = Depends(get_backend_db),
) -> dict:
    """Returns the running and finished jobs for a process."""
    bounds = tuple(map(float, bounds.split(","))) if bounds else None
    from_date = str_to_date(from_date) if from_date else None
    to_date = str_to_date(to_date) if to_date else None
    logger.debug(status)
    try:
        if status is not None and "," in status:
            status = status.split(",")
        status = status if isinstance(status, list) else [status] if status else None
        status = [Status[status] for status in status] if status else None
    except KeyError as exc:
        raise HTTPException(400, f"invalid status: {status}") from exc

    kwargs = {
        "output_path": output_path,
        "status": status,
        "command": command,
        "job_name": job_name,
        "bounds": bounds,
        "from_date": from_date,
        "to_date": to_date,
    }
    logger.debug("job filter kwargs: %s", kwargs)
    return {
        "type": "FeatureCollection",
        "features": [job.to_geojson_dict() for job in backend_db.jobs(**kwargs)],
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str, backend_db: BaseStatusHandler = Depends(get_backend_db)):
    """Returns the status of a job."""
    try:
        return backend_db.job(job_id).to_geojson_dict()
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str, backend_db: BaseStatusHandler = Depends(get_backend_db)
):
    """Cancel a job execution."""
    try:
        job = backend_db.job(job_id)
        if job.status in [
            Status.parsing,
            Status.initializing,
            Status.running,
        ]:  # pragma: no cover
            backend_db.set(job_id, status=Status.cancelled)
            send_slack_message(
                f"*{mhub_settings.self_instance_name}: aborting <{job.url}|{job.job_name}>*"
            )
        # else:
        #     raise AttributeError(f"job status is {job.status}")
        return backend_db.job(job_id).to_geojson_dict()
    except KeyError as exc:
        raise HTTPException(404, f"job {job_id} not found in the database") from exc


@app.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str, backend_db: BaseStatusHandler = Depends(get_backend_db)
):
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
    if job.status == Status.done:
        return job.result

    elif job.status in [
        Status.parsing,
        Status.initializing,
        Status.running,
    ]:  # pragma: no cover
        raise HTTPException(404, f"job {job_id} does not yet have a result")

    elif job.status == Status.cancelled:  # pragma: no cover
        raise HTTPException(
            400,
            {
                "properties": {
                    "type": "Cancelled",
                    "detail": "Job aborted due to user request.",
                }
            },
        )

    elif job.status == Status.failed:
        raise HTTPException(
            400,
            {
                "properties": {
                    "type": job.exception,
                    "detail": job.traceback,
                }
            },
        )
    else:  # pragma: no cover
        raise ValueError(f"invalid job status: {job.status}")
