"""Celery app initialization."""

from flask_celery import Celery


celery_app = Celery(__name__)
