import logging
from shapely import wkt

from mapchete_hub.commands._misc import send_slack_message
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands._execute import mapchete_execute


logger = logging.getLogger(__name__)


# bind=True enables getting the job ID and sending status updates (with send_events())
# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(
    self,
    *args,
    mapchete_config=None,
    process_area=None,
    announce_on_slack=False,
    **kwargs
):
    """Celery task for mapchete_execute."""
    logger.info("got job %s", self.request.id)
    logger.debug("extra kwargs: %s", kwargs)
    process_area = wkt.loads(process_area)
    # print(mapchete_config)

    # send first event in order to have an empty progress_data dictionary
    self.send_event("task-progress", progress_data=dict(current=None, total=None))

    logger.info("preparing execute process")
    # first, the inputs get parsed, i.e. all metadata queried from catalogue
    # this may take a while
    executor = mapchete_execute(
        mapchete_config=mapchete_config, process_area=process_area, **kwargs
    )

    # first item of executor is the number of total tiles; send them to task-progress
    total_tiles = next(executor)
    self.send_event("task-progress", progress_data=dict(current=0, total=total_tiles))

    logger.info("processing %s tiles", total_tiles)
    # iterate over finished process tiles and update task state
    for i, _ in enumerate(executor):
        i += 1
        logger.debug("tile %s/%s finished", i, total_tiles)
        self.send_event("task-progress", progress_data=dict(current=i, total=total_tiles))

    logger.info("processing successful.")
    if announce_on_slack:
        send_slack_message(process_area.centroid.x, process_area.centroid.y)
