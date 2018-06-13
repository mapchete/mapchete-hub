from celery.utils.log import get_task_logger
import logging
import os
from shapely import wkt
from slacker import Slacker

from mapchete_hub import mapchete_index, cleanup_config
from mapchete_hub.celery_app import celery_app


logger = get_task_logger(__name__)
# suppress spam loggers
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("smart_open").setLevel(logging.ERROR)


# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(self, *args, **kwargs):
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
        out_dir=os.environ.get('INDEX_OUTPUT_DIR'),
        gpkg=True
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
    logger.debug(config['mapchete_config'].keys())
    if config['mapchete_config'].get("mhub_announce_on_slack", False):
        logger.debug("announce on slack")
        zone_lat, zone_lon = process_area.centroid.y, process_area.centroid.x
        permalink = "%s#zoom=8&lon=%s&lat=%s" % (
            os.environ.get("PREVIEW_PERMALINK"), zone_lon, zone_lat
        )
        slack = Slacker("", incoming_webhook_url=os.environ["SLACK_WEBHOOK_URL"])
        slack.incomingwebhook.post(
            {
                "username": "Mapchete",
                "icon_url": "https://a2.memecaptain.com/src_thumbs/24132.jpg",
                "channel": "#mapchete_hub",
                "text": permalink
            }
        )
