import logging
from contextlib import contextmanager
from enum import Enum
from typing import Generator, Optional, Union

from aiohttp import ServerConnectionError, ServerDisconnectedError, ServerTimeoutError
from dask.distributed import Client, LocalCluster, get_client
from dask_gateway import BasicAuth, Gateway, GatewayCluster
from mapchete.config.models import DaskSettings, DaskSpecs
from mapchete.executor import DaskExecutor
from pydantic import BaseModel, ConfigDict, Field
from retry import retry

from mapchete_hub.settings import (
    dask_default_specs,
    mhub_settings,
    update_gateway_cluster_options,
)

logger = logging.getLogger(__name__)
CACHE = {}


class ClusterType(str, Enum):
    gateway = "gateway"
    scheduler = "scheduler"
    local = "local"


class ClusterSetup(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: ClusterType = ClusterType.local
    url: Optional[str] = None
    kwargs: Optional[dict] = Field(default_factory=dict)
    cluster: Optional[LocalCluster] = None


def get_dask_cluster_setup() -> ClusterSetup:
    """This allows lazily loading either a LocalCluster, a GatewayCluster or connection to a running scheduler."""
    if mhub_settings.dask_gateway_url:  # pragma: no cover
        return ClusterSetup(
            type=ClusterType.gateway,
            url=mhub_settings.dask_gateway_url,
            kwargs=dict(auth=BasicAuth(password=mhub_settings.dask_gateway_pass)),
        )
    elif mhub_settings.dask_scheduler_url:
        return ClusterSetup(
            type=ClusterType.scheduler, url=mhub_settings.dask_scheduler_url
        )
    else:  # pragma: no cover
        logger.warning(
            "Either MHUB_DASK_GATEWAY_URL and MHUB_DASK_GATEWAY_PASS or MHUB_DASK_SCHEDULER_URL have to be set. "
            "For now, a local cluster is being used."
        )
        if "cluster" in CACHE:
            logger.debug("using cached LocalCluster")
        else:
            logger.debug("creating LocalCluster")
            CACHE["cluster"] = LocalCluster(
                processes=False,
                n_workers=4,
                # threads_per_worker=os.cpu_count()
                threads_per_worker=8,
            )
        return ClusterSetup(type=ClusterType.local, cluster=CACHE["cluster"])


@contextmanager
def get_dask_executor(
    job_id: str,
    dask_specs: DaskSpecs = DaskSpecs(**dask_default_specs),
    dask_settings: DaskSettings = DaskSettings(),
    preprocessing_tasks: Optional[int] = None,
    tile_tasks: Optional[int] = None,
    **kwargs,
) -> Generator[DaskExecutor, None, None]:
    logger.info("requesting dask cluster and dask client...")
    cluster_setup = get_dask_cluster_setup()
    with dask_cluster(cluster_setup, dask_specs=dask_specs) as cluster:
        logger.info("job %s cluster: %s", job_id, cluster)
        with dask_client(cluster_setup, cluster=cluster) as client:
            logger.info("job %s client: %s", job_id, client)
            cluster_adapt(
                cluster_setup,
                cluster,
                dask_specs,
                dask_settings,
                preprocessing_tasks=preprocessing_tasks,
                tile_tasks=tile_tasks,
            )
            with DaskExecutor(dask_client=client) as executor:
                yield executor


@contextmanager
@retry(
    exceptions=(ServerDisconnectedError, ServerConnectionError, ServerTimeoutError),
    tries=mhub_settings.dask_gateway_tries,
    backoff=mhub_settings.dask_gateway_backoff,
    delay=mhub_settings.dask_gateway_delay,
)
def dask_cluster(
    cluster_setup: ClusterSetup, dask_specs: Optional[DaskSpecs] = None
) -> Generator[Union[LocalCluster, GatewayCluster, None], None, None]:
    dask_specs = dask_specs or DaskSpecs(**dask_default_specs)

    if cluster_setup.type == ClusterType.local:
        logger.info("use existing %s", cluster_setup.cluster)
        yield cluster_setup.cluster

    elif cluster_setup.type == ClusterType.gateway:  # pragma: no cover
        with Gateway(cluster_setup.url, **cluster_setup.kwargs) as gateway:
            logger.debug("connected to gateway %s", gateway)
            logger.info("use gateway cluster with %s specs", dask_specs)
            cluster = gateway.new_cluster(
                cluster_options=update_gateway_cluster_options(
                    gateway.cluster_options(), dask_specs=dask_specs
                )
            )
        yield cluster
        logger.info("closing cluster %s", cluster)
        cluster.shutdown()
        logger.info("closed cluster %s", cluster)

    elif cluster_setup.type == ClusterType.scheduler:  # pragma: no cover
        logger.info("cluster exists, connecting directly to scheduler")
        yield None

    else:  # pragma: no cover
        raise TypeError("cannot get cluster")


@contextmanager
def dask_client(
    cluster_setup: ClusterSetup, cluster: Union[LocalCluster, GatewayCluster, None]
) -> Generator[Client, None, None]:
    if cluster_setup.type == ClusterType.local:
        with Client(cluster, set_as_default=False) as client:
            logger.info("started client %s", client)
            yield client
            logger.info("closing client %s", client)
        logger.info("closed client %s", client)

    elif cluster_setup.type == ClusterType.gateway and isinstance(
        cluster, GatewayCluster
    ):  # pragma: no cover
        with cluster.get_client(set_as_default=False) as client:
            logger.info("started client %s", client)
            yield client
            logger.info("closing client %s", client)
        logger.info("closed client %s", client)

    elif cluster_setup.type == ClusterType.scheduler:  # pragma: no cover
        logger.info("connect to scheduler %s", cluster_setup.url)
        yield get_client(cluster_setup.url)
        logger.info("no client to close")
        # NOTE: we don't close the client afterwards as it would affect other jobs using the same client
    else:  # pragma: no cover
        raise TypeError("cannot get client")


def cluster_adapt(
    cluster_setup: ClusterSetup,
    cluster: Union[LocalCluster, GatewayCluster, None],
    dask_specs: DaskSpecs,
    dask_settings: DaskSettings,
    preprocessing_tasks: Optional[int] = None,
    tile_tasks: Optional[int] = None,
):
    if cluster is None:  # pragma: no cover
        logger.debug("cluster does not support adaption")
        return

    adapt_options = dask_specs.adapt_options.model_dump()
    logger.debug("adapt options: %s", adapt_options)

    if preprocessing_tasks is not None and tile_tasks is not None:
        if dask_settings.process_graph:
            # the minimum should be set to the provided minimum but not be larger than the
            # expected number of job tasks
            min_workers = min([dask_specs.adapt_options.minimum, tile_tasks])

            # the maximum should also not be larger than one eigth of the expected number of tasks
            max_workers = min(
                [
                    dask_specs.adapt_options.maximum,
                    ((preprocessing_tasks + tile_tasks) // 8) or 1,
                ]
            )

        else:  # pragma: no cover
            # the minimum should be set to the provided minimum but not be larger than the
            # expected number of job tasks
            min_workers = min([dask_specs.adapt_options.minimum, tile_tasks])

            # the maximum should also not be larger than the expected number of job tasks
            max_workers = min(
                [
                    dask_specs.adapt_options.maximum,
                    max([preprocessing_tasks, tile_tasks]),
                ]
            )

        # max_workers should not be smaller than min_workers
        if max_workers < min_workers:
            max_workers = min_workers

        logger.debug(
            "set minimum workers to %s and maximum workers to %s",
            min_workers,
            max_workers,
        )
        adapt_options.update(
            minimum=min_workers,
            maximum=max_workers,
        )

    logger.debug("set cluster adapt to %s", adapt_options)

    if cluster_setup.type == ClusterType.local or isinstance(
        cluster, LocalCluster
    ):  # pragma: no cover
        cluster.adapt(**{k: v for k, v in adapt_options.items() if k not in ["active"]})

    elif cluster_setup.type == ClusterType.gateway:  # pragma: no cover
        logger.debug("adapt cluster: %s", adapt_options)
        cluster.adapt(**adapt_options)

    else:  # pragma: no cover
        raise TypeError(f"cannot determine cluster type: {cluster}")
