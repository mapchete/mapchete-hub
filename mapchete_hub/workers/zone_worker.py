from billiard import cpu_count
from celery.utils.log import get_task_logger
from mapchete_hub import mapchete_execute
from mapchete_hub.celery_app import celery_app


logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def run(
    self, job_id=None, config=None, mode="continue", zoom=None, bounds=None, debug=False,
    multi=cpu_count(), max_chunksize=1
):
    self.update_state(state='PROGRESS', meta={'current': None, 'total': None})
    executor = mapchete_execute(
        config=config, mode=mode, zoom=zoom, bounds=bounds, debug=debug, multi=multi,
        max_chunksize=max_chunksize
    )
    total_tiles = next(executor)
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': total_tiles})
    logger.debug("total tiles: %s", total_tiles)
    for i, _ in enumerate(executor):
        logger.debug("tile finished")
        self.update_state(state='PROGRESS', meta={'current': i + 1, 'total': total_tiles})
    logger.debug("processing successful.")
