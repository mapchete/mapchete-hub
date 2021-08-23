from dask_gateway_server.options import Options

from mapchete_hub_cli.settings import WORKER_DEFAULT_SPECS


def _get_cluster_specs(gateway, worker_specs):
    options = gateway.cluster_options()
    options.worker_cores = WORKER_DEFAULT_SPECS[worker_specs]["worker_cores"]
    options.worker_memory = WORKER_DEFAULT_SPECS[worker_specs]["worker_memory"]
    options.image = WORKER_DEFAULT_SPECS[worker_specs]["image"]
    return options
