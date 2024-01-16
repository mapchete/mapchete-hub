"""
Slack integration.
"""

import logging
import os

logger = logging.getLogger(__name__)


def send_slack_message(msg):
    """Post preview link on slack."""
    try:
        from slack_sdk.webhook import WebhookClient

        if os.environ.get("SLACK_WEBHOOK_URL"):  # pragma: no cover
            client = WebhookClient(url=os.environ.get("SLACK_WEBHOOK_URL"))
            logger.debug("announce on slack: %s", msg)
            response = client.send(text=msg)
            if response.body != "ok":
                logger.debug("slack message not sent: %s", response.body)
        else:  # pragma: no cover
            logger.debug("no SLACK_WEBHOOK_URL env variable set.")
    except ImportError:  # pragma: no cover
        logger.debug("install 'slack' extra to send messages to slack")
