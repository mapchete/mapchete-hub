from fastapi.testclient import TestClient
import pytest
import mongomock.database

from mapchete_hub.app import app, get_backend_db, get_dask_scheduler
from mapchete_hub.db import BackendDB


def fake_backend_db():
    return BackendDB(mongomock.MongoClient())


def local_dask_scheduler():
    return None

app.dependency_overrides[get_backend_db] = fake_backend_db
app.dependency_overrides[get_dask_scheduler] = local_dask_scheduler


@pytest.fixture
def client():
    _client = TestClient(app)
    return _client


@pytest.fixture
def test_process_id():
    return "mapchete.processes.convert"