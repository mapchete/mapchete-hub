from enum import Enum
from odmantic import Model
from pydantic import BaseModel, Field
from typing import Optional


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
    process: str
    input: dict
    output: dict
    pyramid: dict
    zoom_levels: dict
    config_dir: str = None


class MapcheteJob(BaseModel):
    command: MapcheteCommand
    params: dict
    config: MapcheteProcessConfig


class Progress(BaseModel):
    current: int
    total: int


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
    runtime: Optional[float] = None
    started: Optional[float] = None
    timestamp: Optional[float] = None
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: Optional[str] = None
