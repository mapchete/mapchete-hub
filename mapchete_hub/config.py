import environ
import os


MHUB_DEFAULTS = {
    "config_dir": "/tmp",
    "backend_crs": "EPSG:4326"
}


@environ.config(prefix="MHUB")
class EnvConfig():
    """Configuration from environment."""

    # mhub
    BACKEND_CRS = environ.var(default="EPSG:4326")
    CONFIG_DIR = environ.var(default="/mnt/data")
    BROKER_URI = environ.var(default=None)
    RESULT_BACKEND_URI = environ.var(default=None)
    STATUS_DB_URI = environ.var(default=None)


class DefaultConfig():
    """Default config settings."""

    # celery
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_EVENT_QUEUE_EXPIRES = 60 * 60 * 24  # 1 day
    CELERY_EVENT_SERIALIZER = "json"
    CELERY_IGNORE_RESULT = True
    CELERY_RESULT_BACKEND = "mongodb"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_TASK_ACKS_LATE = True
    CELERY_TASK_ROUTES = {
        "mapchete_hub.commands.execute.*": {"queue": "execute_queue"},
        "mapchete_hub.commands.index.*": {"queue": "index_queue"},
    }
    CELERY_TASK_SEND_SENT_EVENT = True
    CELERY_TASK_SERIALIZER = "json"
    CELERY_WORKER_SEND_TASK_EVENTS = True
    CELERY_WORKER_HIJACK_ROOT_LOGGER = False

    # flask
    DEBUG = False
    ENV = "production"
    MONGO_DBNAME = "mhub"
    TESTING = False


class ProductionConfig(DefaultConfig):
    """Production configuration."""

    pass


class DevelopmentConfig(DefaultConfig):
    """Development configuraion."""

    DEBUG = True
    ENV = "DEBUG"


class TestingConfig(DefaultConfig):
    """Testing configuraion."""

    CELERY_BACKEND_URL = "rpc://"
    CELERY_BROKER_URL = "memory://"
    # tasks won't re-raise exceptions if ignore_result remains True
    CELERY_IGNORE_RESULT = False
    CELERY_RESULT_BACKEND = "cache+memory://"
    CELERY_TASK_ALWAYS_EAGER = False
    ENV = "testing"
    TESTING = True


_configs = {
    "production": ProductionConfig,
    "debug": DevelopmentConfig,
    "testing": TestingConfig,
}


def get_flask_config():
    """Return Flask configuration depending on environment settings."""
    env = os.environ.get("MHUB_ENV", "production")
    config = _configs[env]
    _env = EnvConfig().from_environ()
    if env != "testing":  # pragma: no cover
        config.CELERY_BROKER_URL = _env.BROKER_URI
        config.CELERY_RESULT_BACKEND_URL = _env.RESULT_BACKEND_URI
        config.MONGO_URI = _env.STATUS_DB_URI
    return config


def get_mhub_config():
    """Return mapchete Hub configuration."""
    return EnvConfig().from_environ()
