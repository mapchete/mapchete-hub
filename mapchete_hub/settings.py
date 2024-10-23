"""
Settings.
"""

import logging
import os
from typing import Dict, Literal, Optional, Tuple, Type, TypedDict, Union

from aiohttp import (
    ClientResponseError,
    ServerConnectionError,
    ServerDisconnectedError,
    ServerTimeoutError,
)
from dask.distributed import CancelledError, TimeoutError
from dask_gateway.options import Options
from distributed.comm.core import CommClosedError
from mapchete.config.models import DaskAdaptOptions, DaskSpecs
from pydantic_settings import BaseSettings, SettingsConfigDict

from mapchete_hub import __version__

logger = logging.getLogger(__name__)


PodResources = TypedDict("PodResources", {"memory": str, "cpu": str})

JobWorkerResources = Dict[Literal["requests", "limits"], PodResources]

LogLevels = Literal["notset", "debug", "info", "warning", "error", "critical"]


class MHubSettings(BaseSettings):
    """
    Combine default settings with env variables.

    All settings can be set in the environment by adding the 'MHUB_' prefix
    and the settings in uppercase, e.g. MHUB_SELF_URL.
    """

    self_url: str = "http://127.0.0.1:5000"
    self_instance_name: str = "mapchete Hub (test instance)"
    log_level: LogLevels = "error"
    add_mapchete_logger: bool = False
    backend_db: str = "memory"
    backend_db_event_rate_limit: float = 0.2
    mongodb_timeout: float = 5
    cancellederror_tries: int = 1  # this is deprecated!
    retries: int = 1
    retry_on_exception: Union[Tuple[Type[Exception], ...], Type[Exception]] = (
        CancelledError,
        ClientResponseError,
        CommClosedError,
        ServerConnectionError,
        ServerDisconnectedError,
        ServerTimeoutError,
        TimeoutError,
    )
    job_handler: Literal[
        "background-thread", "k8s-managed-worker", "k8s-job-worker"
    ] = "background-thread"
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
    k8s_namespace: Optional[str] = None
    k8s_image_pull_secret: Optional[str] = None
    k8s_service_account_name: Optional[str] = None
    k8s_worker_default_memory: str = "256Mi"
    k8s_worker_default_cpu: str = "500m"
    k8s_worker_default_memory_limit: str = "512Mi"
    k8s_worker_default_cpu_limit: str = "1"
    k8s_retry_job_x_times: int = 0
    k8s_remove_job_after_seconds: int = 0
    worker_default_image: str = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
    worker_image_tag: str = __version__
    worker_propagate_env_prefixes: str = "AWS, DASK, GDAL, MHUB, MAPCHETE, MP"
    slack_token: Optional[str] = None
    slack_channel: Optional[str] = "mapchete_hub"

    # read from environment
    model_config = SettingsConfigDict(env_prefix="MHUB_")

    def to_k8s_job_worker_resources(self) -> JobWorkerResources:
        return {
            "requests": {
                "memory": self.k8s_worker_default_memory,
                "cpu": self.k8s_worker_default_cpu,
            },
            "limits": {
                "memory": self.k8s_worker_default_memory_limit,
                "cpu": self.k8s_worker_default_cpu_limit,
            },
        }

    def to_env_vars(self) -> Dict[str, str]:
        return {
            f"MHUB_{key.upper()}": str(value)
            for key, value in self.model_dump().items()
            if key not in ["retry_on_exception"] and value is not None
        }

    def to_worker_env_vars(self) -> Dict[str, str]:
        env_vars = {
            key: value
            for key, value in os.environ.items()
            if key.startswith(
                tuple(
                    [
                        prefix.strip()
                        for prefix in mhub_settings.worker_propagate_env_prefixes.split(
                            ","
                        )
                    ]
                )
            )
        }
        return dict(env_vars, **self.to_env_vars())


mhub_settings: MHubSettings = MHubSettings()


DASK_DEFAULT_SPECS = DaskSpecs(
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
    def _enforce_strings_for_worker_env(specs: dict) -> dict:
        if specs.get("worker_environment"):
            specs["worker_environment"] = {
                k: str(v) for k, v in specs["worker_environment"].items()
            }
        return specs

    if specs is None:
        return DASK_DEFAULT_SPECS
    elif isinstance(specs, DaskSpecs):
        specs_dict = {k: v for k, v in specs.model_dump().items() if v is not None}
        return DaskSpecs(
            **dict(DASK_DEFAULT_SPECS, **_enforce_strings_for_worker_env(specs_dict))
        )
    elif isinstance(specs, dict):
        return DaskSpecs(
            **dict(DASK_DEFAULT_SPECS, **_enforce_strings_for_worker_env(specs))
        )
    else:  # pragma: no cover
        raise TypeError(f"unparsable dask specs: {specs}")


def update_gateway_cluster_options(
    options: Options, dask_specs: Optional[DaskSpecs] = None
) -> Options:
    dask_specs = dask_specs or DASK_DEFAULT_SPECS

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


def get_current_env_vars() -> Dict[str, str]:
    return dict(os.environ)
