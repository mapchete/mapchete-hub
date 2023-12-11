"""
Settings.
"""
import logging
import os
from typing import Optional, Union

from dask_gateway.options import Options
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from mapchete_hub import __version__

logger = logging.getLogger(__name__)


class MHubSettings(BaseSettings):
    """
    Combine default settings with env variables.

    All settings can be set in the environment by adding the 'MHUB_' prefix
    and the settings in uppercase, e.g. MHUB_SELF_URL.
    """

    self_url: str = "/"
    self_instance_name: str = "mapchete Hub"
    add_mapchete_logger: bool = False
    backend_db: str = "memory"
    backend_db_event_rate_limit: float = 0.2
    cancellederror_tries: int = 1
    preprocessing_wait: int = 0  # do we need this?
    max_parallel_jobs: int = 2
    max_parallel_jobs_interval_seconds: int = 10
    dask_gateway_url: Optional[str] = None
    dask_gateway_pass: Optional[str] = None
    dask_scheduler_url: Optional[str] = None
    dask_min_workers: int = 10
    dask_max_workers: int = 1000
    dask_adaptive_scaling: bool = True
    worker_default_image: str = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
    worker_image_tag: str = __version__
    worker_propagate_env_prefixes: str = "AWS, DASK, GDAL, MHUB, MAPCHETE, MP"

    # read from environment
    model_config = SettingsConfigDict(env_prefix="MHUB_")


mhub_settings: MHubSettings = MHubSettings()


class DaskAdaptOptions(BaseModel):
    minimum: int = mhub_settings.dask_min_workers
    maximum: int = mhub_settings.dask_max_workers
    active: bool = mhub_settings.dask_adaptive_scaling


class DaskDefaultSpecs(BaseModel):
    worker_cores: float = 0.87
    worker_cores_limit: float = 2.0
    worker_memory: float = 2.1
    worker_memory_limit: float = 12.0
    worker_threads: int = 2
    worker_environment: dict = Field(default_factory=dict)
    scheduler_cores: int = 1
    scheduler_cores_limit: float = 1.0
    scheduler_memory: float = 1.0
    image: str = (
        f"{mhub_settings.worker_default_image}:{mhub_settings.worker_image_tag}"
    )
    adapt_options: DaskAdaptOptions = DaskAdaptOptions()


DASK_DEFAULT_SPECS = {
    "default": DaskDefaultSpecs(),
    "s2_16bit_regular": DaskDefaultSpecs(
        worker_cores=1,
        worker_memory=4.0,
        worker_threads=1,
        scheduler_cores=1,
        scheduler_memory=2.0,
    ),
    "s2_16bit_large": DaskDefaultSpecs(
        worker_cores=1,
        worker_memory=8.0,
        worker_threads=1,
        scheduler_cores=1,
        scheduler_memory=4.0,
    ),
}


def get_dask_specs(specs: Union[str, dict]) -> DaskDefaultSpecs:
    if isinstance(specs, str):
        return DASK_DEFAULT_SPECS[specs]
    elif isinstance(specs, dict):
        return DaskDefaultSpecs(**specs)
    else:
        raise TypeError(
            "specs must refer to a predefined spec "
            f"({', '.join(DASK_DEFAULT_SPECS.keys())}) or a dictionary"
        )


def update_gateway_cluster_options(
    options: Options, dask_specs: Optional[DaskDefaultSpecs] = None
) -> Options:
    dask_specs = dask_specs or DaskDefaultSpecs()

    options.update(
        {
            k: v
            for k, v in dask_specs.model_dump().items()
            if k not in ["adapt_options", "worker_environment"]
        }
    )

    # get selected env variables from mhub and pass it on to the dask scheduler and workers
    # TODO: make less hacky
    env_prefixes = tuple(
        [i.strip() for i in MHubSettings().worker_propagate_env_prefixes.split(",")]
    )
    for k, v in os.environ.items():
        if k.startswith(env_prefixes):
            options.environment[k] = v

    # this allows custom scheduler ENV settings, e.g.:
    # DASK_DISTRIBUTED__SCHEDULER__WORKER_SATURATION="1.0"
    options.environment.update(dask_specs.worker_environment)

    logger.debug("using cluster specs: %s", dict(options))
    return options
