from fastapi.testclient import TestClient
import pytest
import mongomock.database

from mapchete_hub.app import app, get_backend_db, get_dask_scheduler
from mapchete_hub.db import BackendDB

_fake_backend_db = BackendDB(mongomock.MongoClient())


def fake_backend_db():
    return _fake_backend_db


def local_dask_scheduler():
    return None

app.dependency_overrides[get_backend_db] = fake_backend_db
app.dependency_overrides[get_dask_scheduler] = local_dask_scheduler


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def test_process_id():
    return "mapchete.processes.convert"


@pytest.fixture
def example_config_json(tmpdir):
    return {
        "command": "execute",
        "params": {
            "zoom": 8,
            "bounds": [0, 1, 2, 3]
        },
        "config": {
            "process": "mapchete.processes.convert",
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 4,
                "dtype": "uint16",
                "path": str(tmpdir)
            },
            "pyramid": {
                "grid": "geodetic",
                "metatiling": 2
            },
            "zoom_levels": {
                "min": 0,
                "max": 13
            }
        }
    }