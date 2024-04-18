import os

import pytest
from fastapi.testclient import TestClient
from mapchete.path import MPath

from mapchete_hub.app import app

SCRIPT_DIR = MPath(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_process_id():
    return "mapchete.processes.convert"


@pytest.fixture
def test_area_fgb():
    """
    Fixture for test area vector data.
    """
    fgb_path = SCRIPT_DIR / "test_area.fgb"
    if fgb_path.exists():
        return fgb_path.__str__()
    else:
        raise FileNotFoundError


@pytest.fixture
def example_config_json(tmpdir):
    return {
        "command": "execute",
        "params": {"zoom": 5, "bounds": [0, 1, 2, 3]},
        "config": {
            "process": "mapchete.processes.convert",
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 1,
                "dtype": "uint16",
                "path": str(tmpdir),
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    }


@pytest.fixture
def example_config_json_area(tmpdir):
    return {
        "command": "execute",
        "params": {"zoom": 5, "area": "Polygon ((0 1, 2 1, 2 3, 0 3, 0 1))"},
        "config": {
            "process": "mapchete.processes.convert",
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 1,
                "dtype": "uint16",
                "path": str(tmpdir),
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    }


@pytest.fixture
def example_config_json_area_fgb(tmpdir, test_area_fgb):
    return {
        "command": "execute",
        "params": {"zoom": 5, "area": test_area_fgb},
        "config": {
            "process": "mapchete.processes.convert",
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 1,
                "dtype": "uint16",
                "path": str(tmpdir),
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    }


@pytest.fixture
def example_config_custom_process_json(tmpdir):
    return {
        "command": "execute",
        "params": {"zoom": 8, "bounds": [0, 1, 2, 3]},
        "config": {
            "process": [
                "def execute(mp):",
                "    with mp.open('inp') as inp:",
                "        return inp.read()",
            ],
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 1,
                "dtype": "uint16",
                "path": str(tmpdir),
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    }


@pytest.fixture
def example_config_process_exception_json(tmpdir):
    return {
        "command": "execute",
        "params": {"zoom": 8, "bounds": [0, 1, 2, 3]},
        "config": {
            "process": [
                "def execute(mp):",
                "    1/0",
            ],
            "input": {
                "inp": "https://ungarj.github.io/mapchete_testdata/tiled_data/raster/cleantopo/"
            },
            "output": {
                "format": "GTiff",
                "bands": 1,
                "dtype": "uint16",
                "path": str(tmpdir),
            },
            "pyramid": {"grid": "geodetic", "metatiling": 2},
            "zoom_levels": {"min": 0, "max": 13},
        },
    }
