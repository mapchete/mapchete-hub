from fastapi.testclient import TestClient
import pytest

from mapchete_hub.app import app, get_mongo_client


def fake_mongo_client(async_mongodb):
    return async_mongodb


@pytest.fixture
def client():
    _client = TestClient(app)
    # app.mongodb = mongodb
    app.dependency_overrides[get_mongo_client] = fake_mongo_client
    return _client


@pytest.fixture
def test_process_id():
    return "mapchete.processes.convert"