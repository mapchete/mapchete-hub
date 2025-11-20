import logging
from functools import partial
from typing import Optional

from distributed import LocalCluster
from mapchete.commands import execute
from mapchete.commands.observer import Observers
from mapchete.config.models import DaskSettings, DaskSpecs
from mapchete.enums import Status
from mapchete.errors import JobCancelledError
from mapchete.path import MPath

from mapchete_hub.cluster import get_dask_executor
from mapchete_hub.models import JobEntry
from mapchete_hub.settings import mhub_settings

logger = logging.getLogger(__name__)


def job_wrapper(
    job_entry: JobEntry,
    observers: Observers = Observers([]),
    local_cluster: Optional[LocalCluster] = None,
):
    job_id = job_entry.job_id
    job_config = job_entry.mapchete
    logger.info("running job wrapper with job %s", job_id)

    mapchete_config = job_config.config

    # handle observers and job states while job is not being executed
    try:
        # relative output paths are not useful, so raise exception
        out_path = MPath.from_inp(dict(mapchete_config.output))
        if not out_path.is_absolute():  # pragma: no cover
            raise ValueError(f"process output path must be absolute: {out_path}")
    except Exception as exc:  # pragma: no cover
        logger.exception(exc)
        observers.notify(status=Status.failed, exception=exc)
        raise

    # observers and job states are handled by execute() from now on
    try:
        dask_specs = (
            DaskSpecs(**job_config.params.get("dask_specs", {}))
            if isinstance(job_config.params.get("dask_specs", {}), dict)
            else job_config.params.get("dask_specs", {})
        )
        dask_settings = (
            DaskSettings(**job_config.params.get("dask_settings", {}))
            if isinstance(job_config.params.get("dask_settings", {}), dict)
            else job_config.params.get("dask_settings", {})
        )
        execute(
            mapchete_config.model_dump(),
            executor_getter=partial(
                get_dask_executor,
                job_id=job_id,
                dask_specs=dask_specs,
                dask_settings=dask_settings,
                local_cluster=local_cluster,
            ),  # type: ignore
            observers=observers.observers,
            cancel_on_exception=JobCancelledError,
            retries=max(
                [mhub_settings.retries, mhub_settings.cancellederror_tries]
            ),  # this is a workaround to still respect the deprecated "cancellederror_tries" field
            retry_on_exception=mhub_settings.retry_on_exception,
            dask_settings=dask_settings,
            **{
                k: v
                for k, v in job_config.params.items()
                if k not in ["job_name", "dask_specs", "dask_settings"]
            },
        )
        # NOTE: this is not ideal, as we have to get the STACTA path from the output
        observers.notify(
            result={
                "imagesOutput": {
                    "href": mapchete_config.output["path"],
                    "type": "application/json",
                }
            },
        )

    except JobCancelledError:
        logger.info("%s got cancelled.", job_id)
        observers.notify(status=Status.cancelled)
    except Exception as exc:
        logger.exception(exc)
    finally:
        logger.info("%s background task finished", job_id)
