"""
Models and schemas.
"""
import datetime
from enum import Enum
from typing import List, Optional

from mapchete.config import ProcessConfig
from mapchete.config.models import DaskSpecs
from mapchete.enums import Status
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt


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


class GeoJSON(BaseModel):
    type: str = "Feature"
    id: str
    geometry: dict
    bounds: List[float] = None
    area: str = None
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
    started: Optional[datetime.datetime] = None
    finished: Optional[datetime.datetime] = None
    updated: Optional[datetime.datetime] = None
    runtime: Optional[float] = None
    dask_specs: DaskSpecs = DaskSpecs()
    command: Optional[MapcheteCommand] = MapcheteCommand.execute
    job_name: Optional[str] = None
    dask_dashboard_link: Optional[str] = None
    dask_scheduler_logs: Optional[list] = None

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
