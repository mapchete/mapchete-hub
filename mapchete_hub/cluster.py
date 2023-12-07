from contextlib import contextmanager
from enum import Enum
import logging
from typing import Optional, Union

from dask.distributed import Client, get_client, LocalCluster
from dask_gateway import BasicAuth, Gateway, GatewayCluster
from mapchete.executor import DaskExecutor
from pydantic import BaseModel, Field, ConfigDict

from mapchete_hub.settings import update_gateway_cluster_options, mhub_settings

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
                processes=True,
                n_workers=1,
                # threads_per_worker=os.cpu_count()
                threads_per_worker=8,
            )
        return ClusterSetup(type=ClusterType.local, cluster=CACHE["cluster"])


@contextmanager
def get_dask_executor(
    job_id: str, dask_specs: Optional[dict] = None, **kwargs
) -> DaskExecutor:
    logger.info("requesting dask cluster and dask client...")
    cluster_setup = get_dask_cluster_setup()
    with dask_cluster(cluster_setup, dask_specs=dask_specs) as cluster:

        logger.info("job %s cluster: %s", job_id, cluster)
        with dask_client(cluster_setup, cluster=cluster) as client:

            logger.info("job %s client: %s", job_id, client)
            with DaskExecutor(dask_client=client) as executor:

                yield executor


@contextmanager
def dask_cluster(
    cluster_setup: ClusterSetup, dask_specs: Optional[dict] = None
) -> Union[LocalCluster, GatewayCluster, None]:

    dask_specs = dask_specs or {}

    if cluster_setup.type == ClusterType.local:
        logger.info("use existing %s", cluster_setup.cluster)
        yield cluster_setup.cluster

    elif cluster_setup.type == ClusterType.gateway:  # pragma: no cover
        with Gateway(cluster_setup.url, **cluster_setup.kwargs) as gateway:
            logger.debug("connected to gateway %s", gateway)
            if dask_specs is not None:
                logger.info("use gateway cluster with %s specs", dask_specs)
                with gateway.new_cluster(
                    cluster_options=update_gateway_cluster_options(
                        gateway.cluster_options(), dask_specs=dask_specs
                    )
                ) as cluster:
                    yield cluster
                    logger.info("closing cluster %s", cluster)
                logger.info("closed cluster %s", cluster)
            else:
                logger.info("use gateway cluster with default specs")
                with gateway.new_cluster() as cluster:
                    yield cluster
                    logger.info("closing cluster %s", cluster)
                logger.info("closed cluster %s", cluster)

    elif cluster_setup.type == ClusterType.scheduler:  # pragma: no cover
        logger.info("cluster exists, connecting directly to scheduler")
        yield None

    else:  # pragma: no cover
        raise TypeError("cannot get cluster")


@contextmanager
def dask_client(
    cluster_setup: ClusterSetup, cluster: Union[LocalCluster, GatewayCluster, None]
) -> Client:

    if cluster_setup.type == ClusterType.local:
        with Client(cluster, set_as_default=False) as client:
            logger.info("started client %s", client)
            yield client
            logger.info("closing client %s", client)
        logger.info("closed client %s", client)

    elif cluster_setup.type == ClusterType.gateway:  # pragma: no cover
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


def cluster_adapt(cluster, flavor=None, adapt_options=None):
    if cluster is None:  # pragma: no cover
        logger.debug("cluster does not support adaption")
    elif flavor == "local_cluster":  # pragma: no cover
        cluster.adapt(**{k: v for k, v in adapt_options.items() if k not in ["active"]})
    elif flavor == "gateway":  # pragma: no cover
        logger.debug("adapt cluster: %s", adapt_options)
        cluster.adapt(**adapt_options)
    else:  # pragma: no cover
        raise TypeError(f"cannot determine cluster type: {cluster}")
