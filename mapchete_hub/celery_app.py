"""Celery app initialization."""

from celery_slack import Slackify
from flask_celery import Celery
import os


def _get_celery_app():

    celery_app = Celery(__name__)
    # enable app to post task notifications on slack
    if (
        os.environ.get("MHUB_CELERY_SLACK") == "TRUE" and
        os.environ.get("SLACK_WEBHOOK_URL")
    ):
        Slackify(
            celery_app,
            webhook=os.environ.get("SLACK_WEBHOOK_URL"),
            show_beat=False,
            show_startup=False,
            show_shutdown=False,
            show_task_return_value=False,
            show_task_args=False,
            show_task_kwargs=False,
        )
    return celery_app


celery_app = _get_celery_app()
