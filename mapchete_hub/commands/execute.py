import logging
import os
from shapely.geometry import shape
import time

from mapchete_hub.commands._misc import send_slack_message
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands._execute import mapchete_execute


logger = logging.getLogger(__name__)

MHUB_WORKER_EVENT_RATE_LIMIT = os.environ.get("MHUB_WORKER_EVENT_RATE_LIMIT", 1)


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
    """Celery task for mapchete_execute."""
    logger.info("got job %s", self.request.id)
    logger.debug("extra kwargs: %s", kwargs)
    process_area = shape(process_area)
    process_area_process_crs = shape(process_area_process_crs)
    logger.debug("process_area: %s", process_area)
    logger.debug("process_area_process_crs: %s", process_area_process_crs)

    # send first event in order to have an empty progress_data dictionary
    self.send_event("task-progress", progress_data=dict(current=None, total=None))

    logger.info("preparing execute process")
    # first, the inputs get parsed, i.e. all metadata queried from catalogue
    # this may take a while
    executor = mapchete_execute(
        mapchete_config=config,
        process_area=process_area_process_crs,
        mode=params.get("mode"),
        zoom=params.get("zoom"),
        **kwargs
    )
    # first item of executor is the number of total tiles; send them to task-progress
    total_tiles = next(executor)
    self.send_event("task-progress", progress_data=dict(current=0, total=total_tiles))

    logger.info("processing %s tiles", total_tiles)
    # iterate over finished process tiles and update task state
    last_event = 0.
    for i, _ in enumerate(executor):
        i += 1
        logger.debug("tile %s/%s finished", i, total_tiles)
        event_time_passed = time.time() - last_event
        if event_time_passed > MHUB_WORKER_EVENT_RATE_LIMIT or i == total_tiles:
            last_event = time.time()
            self.send_event(
                "task-progress", progress_data=dict(current=i, total=total_tiles)
            )

    logger.info("processing successful.")
    if params.get("announce_on_slack", False):  # pragma: no cover
        send_slack_message(
            process_area_process_crs.centroid.x, process_area_process_crs.centroid.y
        )
