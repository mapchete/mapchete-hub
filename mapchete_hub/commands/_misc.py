import logging
import os
from slacker import Slacker


logger = logging.getLogger(__name__)


def announce_on_slack(mapchete_config=None, process_area=None):
    """Post preview link on slack."""
    if mapchete_config.get("mhub_announce_on_slack", False):
        if not os.environ.get("SLACK_WEBHOOK_URL"):
            logger.error("no SLACK_WEBHOOK_URL env variable set!")
            return
        logger.info("announce on slack")
        Slacker(
            "",
            incoming_webhook_url=os.environ["SLACK_WEBHOOK_URL"]
        ).incomingwebhook.post(
            {
                "username": "Mapchete",
                "icon_url": "https://a2.memecaptain.com/src_thumbs/24132.jpg",
                "channel": "#mapchete_hub",
                "text": "%s#zoom=8&lon=%s&lat=%s" % (
                    os.environ.get("PREVIEW_PERMALINK"),
                    process_area.centroid.y,
                    process_area.centroid.x
                )
            }
        )
