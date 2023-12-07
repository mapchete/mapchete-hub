from dask_gateway.options import Float, Integer, Mapping, Options, String

from mapchete_hub.settings import update_gateway_cluster_options


def test_update_gateway_cluster_options():
    options = update_gateway_cluster_options(
        Options(
            Integer("worker_threads", 1, min=1, max=128),
            Float("worker_cores", 1, min=0.1, max=32),
            Float("worker_cores_limit", 6, min=0.1, max=64),
            Float("worker_memory", 1.0, min=0.1, max=512),
            Float("worker_memory_limit", 12, min=1, max=512),
            Float("scheduler_cores", 0.5, min=0.1, max=32),
            Float("scheduler_cores_limit", 1, min=1, max=32),
            Float("scheduler_memory", 1, min=1, max=128),
            String("image", "foo"),
            Mapping("environment", default={}),
        )
    )
    assert isinstance(options, Options)
    default_options = {
        "worker_cores_limit": 2.0,
        "worker_memory": 2.1,
        "worker_memory_limit": 12.0,
        "worker_threads": 2,
        "scheduler_cores": 1,
        "scheduler_cores_limit": 1.0,
        "scheduler_memory": 1.0,
    }
    for k, v in default_options.items():
        assert options[k] == v
    assert isinstance(options.environment, dict)
    assert options.environment["MHUB_ENV"] == "testing"
