"""
Settings.
"""
import logging
import os

from mapchete_hub import __version__


logger = logging.getLogger(__name__)

WORKER_DEFAULT_IMAGE = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
WORKER_DEFAULT_TAG = os.environ.get("MHUB_IMAGE_TAG", __version__)

DASK_DEFAULT_SPECS = {
    "default": {
        "worker_cores": 0.87,
        "worker_cores_limit": 2.0,
        "worker_memory": 2.1,
        "worker_memory_limit": 12.0,
        "worker_threads": 2,
        "scheduler_cores": 1,
        "scheduler_cores_limit": 1.0,
        "scheduler_memory": 1.0,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}",
        "adapt_options": {
            "minimum": int(os.environ.get("MHUB_DASK_MIN_WORKERS", 10)),
            "maximum": int(os.environ.get("MHUB_DASK_MAX_WORKERS", 1000)),
            "active": os.environ.get("MHUB_DASK_ADAPTIVE_SCALING", "FALSE") == "TRUE",
        },
    },
    "s2_16bit_regular": {
        "worker_cores": 1,
        "worker_memory": 4.0,
        "worker_threads": 1,
        "scheduler_cores": 1,
        "scheduler_memory": 2.0,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}",
    },
    "s2_16bit_large": {
        "worker_cores": 1,
        "worker_memory": 8.0,
        "worker_threads": 1,
        "scheduler_cores": 1,
        "scheduler_memory": 4.0,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}",
    },
    "s1_large": {
        "worker_cores": 8,
        "worker_memory": 16.0,
        "worker_threads": 1,
        "scheduler_cores": 1,
        "scheduler_memory": 2.0,
        "image": f"registry.gitlab.eox.at/maps/mapchete_hub/mhub-s1:{WORKER_DEFAULT_TAG}",
    },
    "custom": {
        "worker_cores": os.environ.get("MHUB_WORKER_CORES", 1),
        "worker_memory": os.environ.get("MHUB_WORKER_MEMORY", 2),
        "worker_threads": os.environ.get("MHUB_WORKER_THREADS", 1),
        "scheduler_cores": os.environ.get("MHUB_SCHEDULER_CORES", 1),
        "scheduler_memory": os.environ.get("MHUB_SCHEDULER_MEMORY", 2),
        "image": f"{os.environ.get('MHUB_WORKER_IMAGE', WORKER_DEFAULT_IMAGE)}:"
        f"{os.environ.get('MHUB_WORKER_IMAGE_TAG', WORKER_DEFAULT_TAG)}",
    },
}


def get_dask_specs(dask_specs="default"):
    """
    Merge user-defined with default specs.
    """
    if isinstance(dask_specs, dict):
        return dict(DASK_DEFAULT_SPECS["default"], **dask_specs)
    return dict(DASK_DEFAULT_SPECS["default"], **DASK_DEFAULT_SPECS[dask_specs])


def get_gateway_cluster_options(gateway, dask_specs="default"):  # pragma: no cover
    options = gateway.cluster_options()
    options.update(
        {
            k: v
            for k, v in get_dask_specs(dask_specs).items()
            if k not in ["adapt_options"]
        }
    )
    logger.debug("using cluster specs: %s", dict(options))
    return options
