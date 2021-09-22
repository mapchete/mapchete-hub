import os

WORKER_DEFAULT_IMAGE = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
WORKER_DEFAULT_TAG = os.environ.get("MHUB_IMAGE_TAG", "0.20")

DASK_DEFAULT_SPECS = {
    "default": {
        "worker_cores": 1,
        "worker_memory": 2.,
        "scheduler_cores": 1,
        "scheduler_memory": 2.,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}"
    },
    "s2_16bit_regular": {
        "worker_cores": 1,
        "worker_memory": 4.,
        "scheduler_cores": 1,
        "scheduler_memory": 2.,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}"
    },
    "s2_16bit_large": {
        "worker_cores": 1,
        "worker_memory": 8.,
        "scheduler_cores": 1,
        "scheduler_memory": 4.,
        "image": f"{WORKER_DEFAULT_IMAGE}:{WORKER_DEFAULT_TAG}"
    },
    "s1_large": {
        "worker_cores": 8,
        "worker_memory": 16.,
        "scheduler_cores": 1,
        "scheduler_memory": 2.,
        "image": "registry.gitlab.eox.at/maps/mapchete_hub/mhub-s1:{WORKER_DEFAULT_TAG}"
    },
    "custom": {
        "worker_cores": os.environ.get("MHUB_WORKER_CORES", 1),
        "worker_memory":  os.environ.get("MHUB_WORKER_MEMORY", 2),
        "scheduler_cores": os.environ.get("MHUB_SCHEDULER_CORES", 1),
        "scheduler_memory": os.environ.get("MHUB_SCHEDULER_MEMORY", 2),
        "image":
            f"{os.environ.get('MHUB_WORKER_IMAGE', WORKER_DEFAULT_IMAGE)}:"
            f"{os.environ.get('MHUB_WORKER_IMAGE_TAG', WORKER_DEFAULT_TAG)}"
    }
}


def _get_cluster_specs(gateway, dask_specs):
    options = gateway.cluster_options()
    options.worker_cores = DASK_DEFAULT_SPECS[dask_specs]["worker_cores"]
    options.worker_memory = DASK_DEFAULT_SPECS[dask_specs]["worker_memory"]
    options.scheduler_cores = DASK_DEFAULT_SPECS[dask_specs]["scheduler_cores"]
    options.scheduler_memory = DASK_DEFAULT_SPECS[dask_specs]["scheduler_memory"]
    options.image = DASK_DEFAULT_SPECS[dask_specs]["image"]
    return options
