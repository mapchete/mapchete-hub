from celery.utils.log import get_task_logger
from shapely import wkt

from mapchete_hub import mapchete_execute, cleanup_config
from mapchete_hub.celery_app import celery_app


logger = get_task_logger(__name__)


# bind=True enables getting the job ID and sending status updates (with send_events())
# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(self, *args, **kwargs):
    logger.info("got job %s", self.request.id)

    # send first event in order to have an empty progress_data dictionary
    self.send_event('task-progress', progress_data=dict(current=None, total=None))

    # first, the inputs get parsed, i.e. all metadata queried from catalogue
    # this may take a while
    executor = mapchete_execute(
        config=cleanup_config(kwargs["config"]['mapchete_config']),
        process_area=wkt.loads(kwargs["process_area"]),
        max_attempts=kwargs.get("max_attempts", 20),
        mode=kwargs["config"].get("mode", "continue")
    )

    # first item of executor is the number of total tiles; send them to task-progress
    total_tiles = next(executor)
    self.send_event('task-progress', progress_data=dict(current=0, total=total_tiles))
    logger.debug("total tiles: %s", total_tiles)

    # iterate over finished process tiles and update task state
    for i, _ in enumerate(executor):
        i += 1
        logger.debug("tile %s/%s finished", i, total_tiles)
        self.send_event('task-progress', progress_data=dict(current=i, total=total_tiles))

    logger.info("processing successful.")
