from collections import OrderedDict
import os
import pytest
import shutil
import yaml

from mapchete_hub.application import flask_app
from mapchete_hub.config import host_options

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")
TEMP_DIR = os.path.join(TESTDATA_DIR, "tmp")


@pytest.fixture
def app():
    """Dummy Flask app."""
    return flask_app()


@pytest.fixture
def baseurl():
    return "http://%s:%s" % (host_options["host_ip"], host_options["port"])


@pytest.fixture
def mp_tmpdir():
    """Setup and teardown temporary directory."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    yield TEMP_DIR
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


@pytest.fixture
def status_gpkg():
    """Setup and teardown temporary directory."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    status_path = os.path.join(TEMP_DIR, 'status.gpkg')
    yield status_path
    try:
        os.remove(status_path)
    except OSError:
        pass


@pytest.fixture
def status_profile():
    return dict(
        crs={'init': 'epsg:4326'},
        driver="GPKG",
        schema=dict(
            geometry='Polygon',
            properties=OrderedDict(
                job_id='str:100',
                config='str:1000',
                state='str:50',
                timestamp='float',
                started='float',
                hostname='str:50',
                progress_data='str:100',
                runtime='float',
                exception='str:100',
                traceback='str:1000',
            )
        )
    )


@pytest.fixture
def example_process():
    return yaml.load(open(os.path.join(TESTDATA_DIR, 'example.mapchete')).read())


@pytest.fixture
def example_config():
    return dict(
        mapchete_config=yaml.load(
            open(os.path.join(TESTDATA_DIR, 'example.mapchete')).read()
        ),
        tile=None,
        mode='continue',
        wkt_geometry=None,
        bounds=[0.0, 1.0, 2.0, 3.0],
        zoom=None,
        point=None
    )
