import datetime
from enum import Enum
from odmantic import Model
from pydantic import BaseModel, Field
from typing import Optional, Union


class State(str, Enum):
    pending = "pending"
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


class MapcheteProcessConfig(BaseModel):
    process: Union[str, list]
    input: dict
    output: dict
    pyramid: dict
    zoom_levels: dict
    bounds: tuple = None
    config_dir: str = None


class MapcheteJob(BaseModel):
    command: MapcheteCommand = Field(None, example="execute")
    params: dict = Field(
        None,
        example={
            "zoom": 8,
            "bounds": [0, 1, 2, 3]
        }
    )
    config: MapcheteProcessConfig = Field(
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
                "path": "/tmp/mhub/"
            },
            "pyramid": {
                "grid": "geodetic",
                "metatiling": 2
            },
            "zoom_levels": {
                "min": 0,
                "max": 13
            }
        }
    )


class Progress(BaseModel):
    current: int
    total: int


class GeoJSON(BaseModel):
    type: str = "Feature"
    id: str = None
    geometry: dict = None
    properties: dict = None


class Job(Model, BaseModel):
    job_id: str
    state: State
    geometry: dict
    mapchete: MapcheteJob
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
    worker_specs: Optional[str] = "default"
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: Optional[str] = None
