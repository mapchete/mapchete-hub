import os

from dask_gateway_server.options import Options

WORKER_DEFAULT_IMAGE = "registry.gitlab.eox.at/maps/mapchete_hub/mhub"
WORKER_DEFAULT_TAG = os.environ.get("MHUB_IMAGE_TAG", "latest")

WORKER_DEFAULT_SPECS = {
    "default": {
        "worker_cores": 1,
        "worker_memory": 2.,
        "image": f"{WORKER_DEFAULT_IMAGE}:fastapi_dask"
    },
    "s2_16bit_regular": {
        "worker_cores": 1,
        "worker_memory": 4.,
        "image": f"{WORKER_DEFAULT_IMAGE}:fastapi_dask"
    },
    "s2_16bit_large": {
        "worker_cores": 1,
        "worker_memory": 8.,
        "image": f"{WORKER_DEFAULT_IMAGE}:fastapi_dask"
    },
    "s1_large": {
        "worker_cores": 8,
        "worker_memory": 16.,
        "image": "registry.gitlab.eox.at/maps/mapchete_hub/mhub-s1:fastapi_dask"
    },
    "custom": {
        "worker_cores": os.environ.get("MHUB_WORKER_CORES"),
        "worker_memory":  os.environ.get("MHUB_WORKER_MEMORY"),
        "image":
            f"{os.environ.get('MHUB_WORKER_IMAGE')}:{os.environ.get('MHUB_WORKER_IMAGE_TAG')}"
    }
}

def cluster_specs_handler(worker_spec):
    options = Options(
        worker_cores=WORKER_DEFAULT_SPECS[worker_spec]["worker_cores"],
        worker_memory=WORKER_DEFAULT_SPECS[worker_spec]["worker_memory"],
        image=WORKER_DEFAULT_SPECS[worker_spec]["image"]
    )
    return options
