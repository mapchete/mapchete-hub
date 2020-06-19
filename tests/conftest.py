from collections import namedtuple, OrderedDict
import os
import oyaml as yaml
import pytest
import rasterio
import requests
import shutil
from tempfile import TemporaryDirectory
import uuid

from mapchete_hub import api
from mapchete_hub.flask_app import flask_app
from mapchete_hub.celery_app import celery_app as celery_test_app

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")
TEMP_DIR = os.path.join(TESTDATA_DIR, "tmp")

TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")
S2_CACHE_DIR = os.path.join(TESTDATA_DIR, "s2_cache")
S1_CACHE_DIR = os.path.join(TESTDATA_DIR, "s1_cache")

ExampleConfig = namedtuple("ExampleConfig", ("path", "dict"))


def _dict_from_mapchete(path, tmpdir):
    conf = dict(yaml.safe_load(open(path).read()), config_dir=os.path.dirname(path))
    if conf["input"] and "s1" in conf["input"]:
        try:
            conf["input"]["s1"]["cache"]["path"] = S1_CACHE_DIR
        except KeyError:
            pass
    else:
        for ip in ["primary", "secondary"]:
            if conf["input"]:
                try:
                    conf["input"][ip]["cache"]["path"] = S2_CACHE_DIR
                except KeyError:
                    pass
    conf["output"].update(path=tmpdir)
    return conf


_test_instance_uri = os.environ.get("MHUB_HOST", "http://localhost:5000/")


@pytest.fixture(scope="session")
def mhub_test_instance_uri():
    return _test_instance_uri


@pytest.fixture(scope="session")
def mhub_test_api():
    return api.API(host=_test_instance_uri)


@pytest.fixture(scope="session")
def wait_for_api():
    response = requests.get("{}capabilities.json".format(_test_instance_uri))
    if response.status_code != 200:
        raise ConnectionError("run docker-compose up -d before running test suite")


@pytest.fixture(scope="session")
def celery_session_app():
    # tests don't work without it ...
    from celery.contrib.testing import tasks

    app = flask_app(full=False)

    # setup and return celery
    celery_test_app.conf.update(app.config)
    celery_test_app.conf.task_ignore_result = False
    celery_test_app.init_app(app)
    yield celery_test_app


@pytest.fixture()
def app(mongodb):
    app = flask_app()
    # replace mongodb backend with pytest fixture
    app.mongodb = mongodb
    return app


@pytest.fixture(scope="session")
def session_client():
    app = flask_app()
    celery_test_app.init_app(app)
    with app.test_client() as c:
        yield c


@pytest.fixture
def client(mongodb):
    app = flask_app()
    # replace mongodb backend with pytest fixture
    app.mongodb = mongodb
    celery_test_app.init_app(app)
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
def test_mapchete():
    path = os.path.join(TESTDATA_DIR, 'test.mapchete')
    with TemporaryDirectory() as temp_dir:
        yield ExampleConfig(path=path, dict=_dict_from_mapchete(path, temp_dir))


@pytest.fixture
def example_custom_process_mapchete():
    path = os.path.join(TESTDATA_DIR, 'example_custom_process.mapchete')
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


test_job_id = uuid.uuid4().hex


@pytest.fixture
def new_job_metadata():
    return {
        "job_id": test_job_id,
        "command": "execute",
        "params": {"bounds": [-1, 0, 0, 1]},
        "config": {
            "output": {
                "path": "test",
                "format": "GTiff"
            },
            "process": "mapchete.processes.examples.example_process",
            "pyramid": {"grid": "geodetic"},
            "zoom_levels": 7,
            "input": None
        },
        "parent_job_id": None,
        "child_job_id": None,
        "process_area": {
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
        },
        "process_area_process_crs": {
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
        },
    }


@pytest.fixture
def event_pending():
    return {
        'args': '()',
        'type': 'task-sent',
        'clock': 90,
        'timestamp': 1528190160.3892283,
        'kwargs': '{"command": "execute", "queue": "execute_queue", "parent_job_id": "", "child_job_id": "", "process_area": "POLYGON ((4 1, 4 2, 3 2, 3 1, 4 1))", "mode": "continue", "bounds": null, "tile": null, "point": null, "mapchete_config": {"process_bounds": [3.0, 1.0, 4.0, 2.0], "some_integer_parameter": 12, "some_bool_parameter": true, "some_float_parameter": 5.3, "output": {"dtype": "float32", "bands": 1, "path": "test", "format": "GTiff"}, "process_file": "example_process.py", "some_string_parameter": {"zoom<=7": "string1", "zoom>7": "string2"}, "zoom_levels": {"min": 7, "max": 11}, "pyramid": {"grid": "geodetic", "metatiling": 4}, "input": {"file1": {"zoom>=10": "dummy1.tif"}, "file2": "dummy2.tif"}}, "wkt_geometry": null, "zoom": null}',
        'root_id': 'hanse',
        'hostname': 'gen6329@tycho2',
        'local_received': 1528190160.3903759,
        'uuid': test_job_id,
        'routing_key': 'zone_queue',
        'eta': None,
        'name': 'mapchete_hub.workers.zone_worker.run',
        'exchange': '',
        'expires': None,
        'retries': 0,
        'utcoffset': -2,
        'state': 'PENDING',
        'queue': 'zone_queue',
        'parent_id': None,
        'pid': 6329
    }


@pytest.fixture
def event_progress():
    return {
        'utcoffset': -2,
        'timestamp': 1528185898.6538837,
        'clock': 3,
        'type': 'task-progress',
        'pid': 31546,
        'hostname': 'zone_worker@tycho2',
        'progress_data': {'current': 3, 'total': 24},
        'state': 'PROGRESS',
        'uuid': test_job_id,
        'local_received': 1528185898.7191732
    }


@pytest.fixture
def event_success():
    return {
        'clock': 64,
        'pid': 20106,
        'uuid': test_job_id,
        'runtime': 40.91311929101357,
        'state': 'SUCCESS',
        'timestamp': 1527938183.97571,
        'hostname': 'zone_worker@tycho2',
        'utcoffset': -2,
        'local_received': 1527938183.9801202,
        'result': 'None',
        'type': 'task-succeeded'
    }


@pytest.fixture
def event_failure():
    return {
        'utcoffset': -2,
        'pid': 16322,
        'local_received': 1527934867.8697965,
        'traceback': 'Traceback (most recent call last):  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 382, in trace_task\n    R = retval = fun(*args, **kwargs)\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 641, in __protected_call__\n    return self.run(*args, **kwargs)\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/workers/zone_worker.py", line 24, in run\n    for i, _ in enumerate(executor):\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 39, in mapchete_execute\n    chunksize=min([max([total_tiles // multi, 1]), max_chunksize])\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 1920, in next\n    raise Exception(value)\nException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 358, in workloop\n    result = (True, prepare_result(fun(*args, **kwargs)))\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 79, in _process_worker\n    output = process.execute(process_tile, raise_nodata=True)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 268, in execute\n    return self._execute(process_tile, raise_nodata=raise_nodata)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 507, in _execute\n    raise MapcheteProcessException(format_exc())\nmapchete.errors.MapcheteProcessException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\n\n', 'exception': 'Exception(<ExceptionInfo: MapcheteProcessException(\'Traceback (most recent call last):\\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\\n    process_data = self.config.process_func(tile_process)\\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\\n    assert randint(0, 500)\\nAssertionError\\n\',)>,)',
        'uuid': test_job_id,
        'type': 'task-failed',
        'hostname': 'zone_worker@tycho2',
        'timestamp': 1527934867.8687088,
        'clock': 10,
        'state': 'FAILURE'
    }
