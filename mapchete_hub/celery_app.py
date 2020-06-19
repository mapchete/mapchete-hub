from flask_celery import Celery

from mapchete_hub.config import get_flask_config


def _celery_app():
    """Initialize and return Celery app."""
    app = Celery(__name__)
    # configure app
    app.config_from_object(get_flask_config())
    return app

celery_app = _celery_app()
