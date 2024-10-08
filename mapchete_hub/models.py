"""
Models and schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from mapchete.config import ProcessConfig
from mapchete.config.models import DaskSpecs
from mapchete.enums import Status
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, NonNegativeInt

from mapchete_hub.random_names import random_name
from mapchete_hub.timetools import parse_to_date


class MapcheteCommand(str, Enum):
    # convert = "convert"
    # cp = "cp"
    execute = "execute"
    # index = "index"


class MapcheteJob(BaseModel):
    command: MapcheteCommand = Field(None, examples=["execute"])
    params: dict = Field(None, examples=[{"zoom": 8, "bounds": [0, 1, 2, 3]}])
    config: ProcessConfig = Field(
        None,
        examples=[
            {
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
            }
        ],
    )


class GeoJSON(BaseModel):
    type: str = "Feature"
    id: str
    geometry: dict
    bounds: Optional[List[float]] = None
    area: Optional[str] = None
    properties: dict = Field(default_factory=dict)

    @property
    def __geo_interface__(self):
        return self.geometry

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "geometry": self.geometry,
            "bounds": self.bounds,
            "area": self.area,
            "properties": self.properties,
        }


class JobEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    job_id: str
    url: str
    state: Optional[str] = None  # this is deprecated
    status: Status
    geometry: dict
    bounds: List[float]
    mapchete: MapcheteJob
    area: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    output_path: Optional[str] = None
    result: dict = Field(default_factory=dict)
    previous_job_id: Optional[str] = None
    next_job_id: Optional[str] = None
    current_progress: Optional[NonNegativeInt] = None
    total_progress: Optional[NonNegativeInt] = None
    submitted: Optional[AwareDatetime] = None
    started: Optional[AwareDatetime] = None
    finished: Optional[AwareDatetime] = None
    updated: Optional[AwareDatetime] = None
    runtime: Optional[float] = None
    dask_specs: DaskSpecs = DaskSpecs()
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: str = Field(default_factory=random_name)
    dask_dashboard_link: Optional[str] = None
    dask_scheduler_logs: Optional[list] = None
    slack_thread_ds: Optional[str] = None
    slack_channel_id: Optional[str] = None

    def update(self, **new_data):
        for field, value in new_data.items():
            setattr(self, field, value)

    def to_geojson(self) -> GeoJSON:
        return GeoJSON(
            type="Feature",
            id=self.job_id,
            geometry=self.geometry,
            bounds=self.bounds,
            properties={
                k: v
                for k, v in self.model_dump().items()
                if k not in ["job_id", "geometry", "id", "_id", "bounds"]
            },
        )

    def to_geojson_dict(self) -> dict:
        return self.to_geojson().to_dict()

    @property
    def __geo_interface__(self):
        return self.geometry

    @staticmethod
    def from_dict(kwargs: dict) -> JobEntry:
        # parse timestamps to timezone-aware datetime objects
        for key in ["submitted", "started", "finished", "updated"]:
            value = kwargs.get(key)
            if value is not None:
                kwargs[key] = parse_to_date(value)
        return JobEntry(**kwargs)


def to_status(status: Union[Status, str]) -> Status:
    if isinstance(status, Status):
        return status
    return Status[status]


def to_status_list(
    statuses: Union[Status, str, List[Status], List[str]],
) -> List[Status]:
    if isinstance(statuses, str):
        return [to_status(status_str) for status_str in statuses.split(",")]
    elif isinstance(statuses, Status):
        return [statuses]
    elif isinstance(statuses, list):
        return [to_status(status) for status in statuses]
    raise TypeError(f"cannot convert {statuses} to list of Status instances")
