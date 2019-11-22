from case import ContextMock, Mock
from collections import namedtuple, OrderedDict
import os
import pytest
import rasterio
import shutil
from tempfile import TemporaryDirectory
import oyaml as yaml

from mapchete_hub import api
from mapchete_hub.application import flask_app
from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import host_options, flask_options

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")
TEMP_DIR = os.path.join(TESTDATA_DIR, "tmp")

TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")
S2_CACHE_DIR = os.path.join(TESTDATA_DIR, "s2_cache")
S1_CACHE_DIR = os.path.join(TESTDATA_DIR, "s1_cache")


ExampleConfig = namedtuple("ExampleConfig", ("path", "dict"))


# making celery.send_event() work with eager mode:
def send_task(name, args=(), kwargs={}, **opts):
    # https://github.com/celery/celery/issues/581
    task = celery_app.tasks[name]
    return task.apply(args, kwargs, **opts)
celery_app.send_task = send_task

# mocking send_event() calls
celery_app.events = Mock(name='events')
celery_app.events.attach_mock(ContextMock(), 'default_dispatcher')
celery_app.conf.update(flask_options, task_always_eager=True)


def _dict_from_mapchete(path, tmpdir):
    conf = dict(yaml.safe_load(open(path).read()), config_dir=os.path.dirname(path))
    if "s1" in conf["input"]:
        try:
            conf["input"]["s1"]["cache"]["path"] = S1_CACHE_DIR
        except KeyError:
            pass
    else:
        for ip in ["primary", "secondary"]:
            try:
                conf["input"][ip]["cache"]["path"] = S2_CACHE_DIR
            except KeyError:
                pass
    conf["output"].update(path=tmpdir)
    return conf


@pytest.fixture(scope="session")
def client():
    app = flask_app()
    celery_app.init_app(app)
    with app.test_client() as c:
        yield c


@pytest.fixture
def mhub_api(client):
    return api.API(_test_client=client)


@pytest.fixture(scope="session")
def aws_example_mapchete_cm_4b():
    """Fixture for aws_example.mapchete."""
    with TemporaryDirectory() as temp_dir:
        yield _dict_from_mapchete(
            os.path.join(TESTDATA_DIR, "aws_example_4bands.mapchete"), temp_dir
        )


@pytest.fixture(scope="session")
def mundi_example_mapchete_gamma0():
    """Fixture for aws_example.mapchete."""
    with TemporaryDirectory() as temp_dir:
        yield _dict_from_mapchete(
            os.path.join(TESTDATA_DIR, "s1_example.mapchete"), temp_dir
        )


@pytest.fixture
def aws_example_mapchete_cm_4b_path():
    """Fixture for aws_example.mapchete."""
    return os.path.join(TESTDATA_DIR, "aws_example_4bands.mapchete")


@pytest.fixture
def landpoly_geojson():
    """Fixture for landpoly.geojson."""
    return os.path.join(TESTDATA_DIR, "landpoly.geojson")


@pytest.fixture
def tile_13_1986_8557_geojson():
    """Fixture for tile_13_1986_8557.geojson."""
    return os.path.join(TESTDATA_DIR, "tile_13_1986_8557.geojson")


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
    with TemporaryDirectory() as temp_dir:
        yield os.path.join(temp_dir, 'status.gpkg')


@pytest.fixture
def status_profile():
    return dict(
        crs={'init': 'epsg:4326'},
        driver="GPKG",
        schema=dict(
            geometry='Polygon',
            properties=OrderedDict(
                command="str:20",
                config="str:1000",
                exception="str:100",
                hostname="str:50",
                job_id="str:100",
                job_name="str:100",
                parent_job_id="str:100",
                child_job_id="str:100",
                progress_data="str:100",
                queue="str:50",
                runtime="float",
                started="float",
                state="str:50",
                timestamp="float",
                traceback="str:1000",
            )
        )
    )


@pytest.fixture
def example_mapchete():
    path = os.path.join(TESTDATA_DIR, 'example.mapchete')
    with TemporaryDirectory() as temp_dir:
        yield ExampleConfig(path=path, dict=_dict_from_mapchete(path, temp_dir))


@pytest.fixture
def batch_example():
    path = os.path.join(TESTDATA_DIR, 'batch_example.mhub')
    yield ExampleConfig(path=path, dict=yaml.safe_load(open(path)))


@pytest.fixture
def batch_example_no_jobs_error():
    path = os.path.join(TESTDATA_DIR, 'batch_example_no_jobs_error.mhub')
    yield ExampleConfig(path=path, dict=yaml.safe_load(open(path)))


@pytest.fixture
def batch_example_invalid_job_pointer_error():
    path = os.path.join(TESTDATA_DIR, 'batch_example_invalid_job_pointer_error.mhub')
    yield ExampleConfig(path=path, dict=yaml.safe_load(open(path)))


@pytest.fixture
def batch_example_no_job_mapchete_error():
    path = os.path.join(TESTDATA_DIR, 'batch_example_no_job_mapchete_error.mhub')
    yield ExampleConfig(path=path, dict=yaml.safe_load(open(path)))


@pytest.fixture
def batch_example_no_command_error():
    path = os.path.join(TESTDATA_DIR, 'batch_example_no_command_error.mhub')
    yield ExampleConfig(path=path, dict=yaml.safe_load(open(path)))


@pytest.fixture
def example_config():
    return dict(
        mapchete_config=yaml.safe_load(
            open(os.path.join(TESTDATA_DIR, 'example.mapchete')).read()
        ),
        tile=None,
        mode='continue',
        wkt_geometry=None,
        bounds=[0.0, 1.0, 2.0, 3.0],
        zoom=None,
        point=None
    )


@pytest.fixture(scope="session")
def dummy1_tif():
    return os.path.join(TESTDATA_DIR, "dummy1.tif")


@pytest.fixture(scope="session")
def array_8bit(dummy1_tif):
    with rasterio.open(dummy1_tif) as src:
        return src.read()


@pytest.fixture
def response_json():
    return {
        'properties': {'state': 'PENDING'},
        'geometry': {
            'coordinates': [
                [
                    [2.109375, 3.8671875],
                    [2.109375, 4.21875],
                    [1.7578125, 4.21875],
                    [1.7578125, 3.8671875],
                    [2.109375, 3.8671875]
                ]
            ],
            'type': 'Polygon'
        }
    }
