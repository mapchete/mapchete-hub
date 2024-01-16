"""
Settings.
"""
import logging
import os
from typing import Optional, Union

from dask_gateway.options import Options
from mapchete.config.models import DaskAdaptOptions, DaskSpecs
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

    self_url: str = "http://127.0.0.1:5000"
    self_instance_name: str = "mapchete Hub (test instance)"
    add_mapchete_logger: bool = False
    backend_db: str = "memory"
    backend_db_event_rate_limit: float = 0.2
    cancellederror_tries: int = 1
    max_parallel_jobs: int = 2
    max_parallel_jobs_interval_seconds: int = 10
    dask_gateway_url: Optional[str] = None
    dask_gateway_pass: Optional[str] = None
    dask_gateway_tries: int = 1
    dask_gateway_backoff: float = 1.0
    dask_gateway_delay: float = 0.0
    dask_scheduler_url: Optional[str] = None
    dask_min_workers: int = 10
    dask_max_workers: int = 1000
    dask_adaptive_scaling: bool = True
    worker_default_image: str = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
    worker_image_tag: str = __version__
    worker_propagate_env_prefixes: str = "AWS, DASK, GDAL, MHUB, MAPCHETE, MP"
    slack_token: Optional[str] = None
    slack_channel: Optional[str] = "mapchete_hub"

    # read from environment
    model_config = SettingsConfigDict(env_prefix="MHUB_")


mhub_settings: MHubSettings = MHubSettings()


dask_default_specs = dict(
    worker_cores=0.87,
    worker_cores_limit=2.0,
    worker_memory=2.1,
    worker_memory_limit=12.0,
    worker_threads=2,
    worker_environment={},
    scheduler_cores=1,
    scheduler_cores_limit=1.0,
    scheduler_memory=1.0,
    image=f"{mhub_settings.worker_default_image}:{mhub_settings.worker_image_tag}",
    adapt_options=DaskAdaptOptions(
        minimum=mhub_settings.dask_min_workers,
        maximum=mhub_settings.dask_max_workers,
        active=mhub_settings.dask_adaptive_scaling,
    ),
)


def get_dask_specs(specs: Optional[Union[DaskSpecs, dict]] = None) -> DaskSpecs:
    if specs is None:
        return DaskSpecs(**dask_default_specs)
    elif isinstance(specs, DaskSpecs):
        specs_dict = {k: v for k, v in specs.model_dump().items() if v is not None}
        return DaskSpecs(**dict(dask_default_specs, **specs_dict))
    elif isinstance(specs, dict):
        return DaskSpecs(**dict(dask_default_specs, **specs))
    else:  # pragma: no cover
        raise TypeError(f"unparsable dask specs: {specs}")


def update_gateway_cluster_options(
    options: Options, dask_specs: Optional[DaskSpecs] = None
) -> Options:
    dask_specs = dask_specs or DaskSpecs(**dask_default_specs)

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
