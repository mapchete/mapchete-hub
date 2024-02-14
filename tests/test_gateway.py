import pytest
from mapchete.executor import DaskExecutor

from mapchete_hub.cluster import get_dask_executor
from mapchete_hub.settings import mhub_settings


@pytest.mark.skipif(
    mhub_settings.dask_gateway_url is None or mhub_settings.dask_gateway_pass is None,
    reason="MHUB_DASK_GATEWAY_URL and MHUB_DASK_GATEWAY_PASS must be set",
)
def test_gateway_executor():

    def dummy_task(*_, **__):
        return True

    with get_dask_executor(
        job_id="test_job",
        preprocessing_tasks=1,
        tile_tasks=1,
    ) as executor:
        assert isinstance(executor, DaskExecutor)
        for future in executor.map(dummy_task, range(10)):
            assert future is True
