from enum import Enum
from pydantic import BaseModel, Field
from odmantic import Model
from typing import Optional


class State(str, Enum):
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


class MapcheteConfig(BaseModel):
    process: str
    input: dict
    output: dict
    pyramid: dict
    zoom_levels: dict


class Mapchete(BaseModel):
    command: MapcheteCommand
    params: dict
    config: MapcheteConfig


class Progress(BaseModel):
    current: int
    total: int


class Job(Model, BaseModel):
    job_id: str
    state: State
    geometry: dict
    mapchete: Mapchete
    exception: Optional[str] = None
    traceback: Optional[str] = None
    output_path: Optional[str] = None
    result: Optional[dict] = None
    previous_job_id: Optional[str] = None
    next_job_id: Optional[str] = None
    progress: Optional[Progress] = None
    runtime: Optional[float] = None
    started: Optional[float] = None
    timestamp: Optional[float] = None
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: Optional[str] = None
