import logging
from mapchete.io import makedirs
import os
from shapely.geometry import shape

from mapchete_hub.commands._misc import send_slack_message
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands._index import mapchete_index


logger = logging.getLogger(__name__)


# bind=True enables getting the job ID and sending status updates (with send_events())
@celery_app.task(bind=True)
def run(
    self,
    *args,
    params=None,
    config=None,
    process_area=None,
    process_area_process_crs=None,
    **kwargs
):
    """Celery task for mapchete_index."""
    logger.info("got job %s", self.request.id)
    logger.debug("extra kwargs: %s", kwargs)
    process_area = shape(process_area)
    process_area_process_crs = shape(process_area_process_crs)
    logger.debug("process_area: %s", process_area)
    logger.debug("process_area_process_crs: %s", process_area_process_crs)

    # send first event in order to have an empty progress_data dictionary
    self.send_event('task-progress', progress_data=dict(current=None, total=None))

    # first, the inputs get parsed, i.e. all metadat queried from catalogue
    # this may take a while
    if "MHUB_INDEX_OUTPUT_DIR" in os.environ:  # pragma: no cover
        # create subfolder using process output path in order not to mix up index files
        # from multiple outputs
        index_output_path = os.path.join(
            os.environ.get("MHUB_INDEX_OUTPUT_DIR"),
            os.path.join(
                *config["output"]["path"].replace("s3://", "").split("/")
            )
        )
        makedirs(index_output_path)
    else:
        index_output_path = config["output"]["path"]

    logger.info("preparing execute process")
    executor = mapchete_index(
        mapchete_config=config,
        process_area=process_area_process_crs,
        mode=params.get("mode"),
        zoom=params.get("zoom"),
        shapefile=True,
        out_dir=index_output_path,
        **kwargs
    )

    # get total tiles
    total_tiles = next(executor)
    self.send_event('task-progress', progress_data=dict(current=0, total=total_tiles))
    logger.info("indexing from %s process tiles", total_tiles)

    # iterate over finished process tiles and update task state
    for i, _ in enumerate(executor):
        i += 1
        logger.debug("tile %s/%s finished", i, total_tiles)
        self.send_event('task-progress', progress_data=dict(current=i, total=total_tiles))

    logger.info("processing successful.")
    if params.get("announce_on_slack", False):  # pragma: no cover
        send_slack_message(
            process_area_process_crs.centroid.x, process_area_process_crs.centroid.y
        )
