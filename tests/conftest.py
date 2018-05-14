import pytest

from mapchete_hub.application import flask_app
from mapchete_hub.config import get_host_options


@pytest.fixture
def app():
    """Dummy Flask app."""
    return flask_app()


@pytest.fixture
def baseurl():
    host_opts = get_host_options()
    return "http://%s:%s" % (host_opts["host_ip"], host_opts["port"])
