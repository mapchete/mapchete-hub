"""
Slack integration.
"""

import logging
import os


logger = logging.getLogger(__name__)


def send_slack_message(msg):
    """Post preview link on slack."""
    try:
        from slacker import Slacker

        if os.environ.get("SLACK_WEBHOOK_URL"):  # pragma: no cover
            logger.debug("announce on slack: %s", msg)
            Slacker(
                None, incoming_webhook_url=os.environ["SLACK_WEBHOOK_URL"]
            ).incomingwebhook.post(
                {"username": "mapchete_hub", "channel": "#mapchete_hub", "text": msg}
            )
        else:  # pragma: no cover
            logger.error("no SLACK_WEBHOOK_URL env variable set.")
    except ImportError:
        logger.error("install 'slack' extra for this feature")
