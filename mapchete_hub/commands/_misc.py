import logging
import os
from slacker import Slacker


logger = logging.getLogger(__name__)


def send_slack_message(x, y):
    """Post preview link on slack."""
    if os.environ.get("SLACK_WEBHOOK_URL"):
        logger.info("announce on slack")
        Slacker(
            None,
            incoming_webhook_url=os.environ["SLACK_WEBHOOK_URL"]
        ).incomingwebhook.post(
            {
                "username": "mapchete_hub",
                "channel": "#mapchete_hub",
                "text": "%s#zoom=8&lon=%s&lat=%s" % (
                    os.environ.get("PREVIEW_PERMALINK"), y, x
                )
            }
        )
    else:
        logger.error("no SLACK_WEBHOOK_URL env variable set!")
