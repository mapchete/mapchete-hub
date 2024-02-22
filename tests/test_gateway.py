import os

import pytest
from mapchete.executor import DaskExecutor

from mapchete_hub.cluster import ClusterSetup, get_dask_executor
from mapchete_hub.settings import MHubSettings

dask_gateway_url = os.environ.get("MHUB_TEST_DASK_GATEWAY_URL")
dask_gateway_pass = os.environ.get("MHUB_TEST_DASK_GATEWAY_PASS")


@pytest.mark.skipif(
    dask_gateway_url is None or dask_gateway_pass is None,
    reason="MHUB_TEST_DASK_GATEWAY_URL and MHUB_TEST_DASK_GATEWAY_PASS must be set",
)
def test_gateway_executor():
    def dummy_task(*_, **__):
        return True

    with get_dask_executor(
        job_id="test_job",
        preprocessing_tasks=1,
        tile_tasks=1,
        cluster_setup=ClusterSetup(
            MHubSettings(
                dask_gateway_url=dask_gateway_url, dask_gateway_pass=dask_gateway_pass
            )
        ),
    ) as executor:
        assert isinstance(executor, DaskExecutor)
        for result in executor.map(dummy_task, range(10)):
            assert result
