from billiard import cpu_count
from celery.utils.log import get_task_logger
from mapchete_hub import mapchete_execute
from mapchete_hub.celery_app import celery_app


logger = get_task_logger(__name__)


# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(
    self,
    config=None,
    mode="continue",
    zoom=None,
    bounds=None,
    multi=cpu_count(),
    max_chunksize=1
):
    self.send_event('task-progress', progress_data=dict(current=None, total=None))
    logger.debug("initialize process")
    # first, the inputs get parsed, i.e. all metadat queried from catalogue
    # this may take a while
    executor = mapchete_execute(
        config=config, mode=mode, zoom=zoom, bounds=bounds, multi=multi,
        max_chunksize=max_chunksize
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
