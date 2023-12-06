"""
Models and schemas.
"""
import datetime
from enum import Enum
from typing import Optional, Union

from mapchete.config import ProcessConfig
from pydantic import BaseModel, Field


# TODO: take from core package
class State(str, Enum):
    pending = "pending"
    created = "created"
    initializing = "initializing"
    running = "running"
    aborting = "aborting"
    cancelled = "cancelled"
    failed = "failed"
    done = "done"


class MapcheteCommand(str, Enum):
    # convert = "convert"
    # cp = "cp"
    execute = "execute"
    # index = "index"


class MapcheteJob(BaseModel):
    command: MapcheteCommand = Field(None, example="execute")
    params: dict = Field(None, example={"zoom": 8, "bounds": [0, 1, 2, 3]})
    config: ProcessConfig = Field(
        None,
        example={
            "process": "mapchete.processes.convert",
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 4,
                "dtype": "uint16",
                "path": "/tmp/mhub/",
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    )


# TODO: take from core package
class Progress(BaseModel):
    current: int
    total: int


class GeoJSON(BaseModel):
    type: str = "Feature"
    id: str = None
    geometry: dict = None
    bounds: list = None
    area: str = None
    properties: dict = None


class JobEntry(BaseModel):
    job_id: str
    url: str
    state: State
    geometry: dict
    bounds: list
    mapchete: MapcheteJob
    area: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    output_path: Optional[str] = None
    result: Optional[dict] = None
    previous_job_id: Optional[str] = None
    next_job_id: Optional[str] = None
    progress: Optional[Progress] = None
    started: Optional[datetime.datetime] = None
    finished: Optional[datetime.datetime] = None
    updated: Optional[datetime.datetime] = None
    runtime: Optional[float] = None
    dask_specs: Union[dict, str, None] = None
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: Optional[str] = None
    dask_dashboard_link: Optional[str] = None
    dask_scheduler_logs: Optional[list] = None
