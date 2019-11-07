from celery.utils.log import get_task_logger
from mapchete.io import makedirs
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
    if "INDEX_OUTPUT_DIR" in os.environ:
        # create subfolder using process output path in order not to mix up index files
        # from multiple outputs
        index_output_path = os.path.join(
            os.environ.get("INDEX_OUTPUT_DIR"),
            os.path.join(
                *mapchete_config["output"]["path"].replace("s3://", "").split("/")
            )
        )
        makedirs(index_output_path)
    else:
        index_output_path = mapchete_config["output"]["path"]
    executor = mapchete_index(
        config=mapchete_config,
        process_area=process_area,
        out_dir=index_output_path,
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
