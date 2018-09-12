from celery.utils.log import get_task_logger
import logging
from shapely import wkt

from mapchete_hub import mapchete_execute, cleanup_config
from mapchete_hub.celery_app import celery_app


logger = get_task_logger(__name__)


# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(self, *args, **kwargs):
    config = kwargs["config"]
    logger.debug("got job %s", self.request.id)
    process_area = kwargs["process_area"]
    self.send_event('task-progress', progress_data=dict(current=None, total=None))
    mapchete_config = cleanup_config(config['mapchete_config'])
    # first, the inputs get parsed, i.e. all metadata queried from catalogue
    # this may take a while
    executor = mapchete_execute(
        config=mapchete_config, process_area=wkt.loads(process_area),
        max_attempts=kwargs.get("max_attempts", 20), mode=config["mode"]
    )

    # get total tiles
    total_tiles = next(executor)
    self.send_event('task-progress', progress_data=dict(current=0, total=total_tiles))
    logger.debug("total tiles: %s", total_tiles)

    # iterate over finished process tiles and update task state
    for i, _ in enumerate(executor):
        i += 1
        logger.debug("tile %s/%s finished", i, total_tiles)
        self.send_event('task-progress', progress_data=dict(current=i, total=total_tiles))

    logger.debug("processing successful.")
