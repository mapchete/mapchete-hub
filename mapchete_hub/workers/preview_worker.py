from celery.utils.log import get_task_logger
import os
from shapely import wkt

from mapchete_hub import mapchete_index, cleanup_config
from mapchete_hub.celery_app import celery_app
from mapchete_hub._misc import announce_on_slack


logger = get_task_logger(__name__)


# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(self, *args, **kwargs):
    logger.info("got job %s", self.request.id)
    config = kwargs["config"]
    logger.debug(config)
    process_area = wkt.loads(kwargs["process_area"])
    logger.debug("initialize process")
    self.send_event('task-progress', progress_data=dict(current=None, total=None))
    mapchete_config = cleanup_config(config['mapchete_config'])
    # first, the inputs get parsed, i.e. all metadat queried from catalogue
    # this may take a while
    executor = mapchete_index(
        config=mapchete_config,
        process_area=process_area,
        out_dir=os.environ.get('INDEX_OUTPUT_DIR', mapchete_config["output"]["path"]),
        shapefile=True
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

    logger.info("processing successful.")
    announce_on_slack(config=config, process_area=process_area)
