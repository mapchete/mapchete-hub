from mapchete.errors import MapcheteProcessException
import os
import pytest
from shapely.geometry import box

from mapchete_hub import mapchete_index, mapchete_execute, cleanup_config


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")


def test_cleanup_config(example_process):
    assert [k for k in example_process.keys() if k.startswith("mhub_")]
    cleaned = cleanup_config(example_process)
    assert not [k for k in cleaned.keys() if k.startswith("mhub_")]


def test_mapchete_index(mp_tmpdir, example_process):
    assert(len(list(mapchete_index(
        config=example_process,
        shapefile=True,
        out_dir=mp_tmpdir
    ))))


def test_workerlost(mp_tmpdir, example_process):
    mp_config = cleanup_config(dict(example_process, process="workerlost.py"))
    for i in range(1):
        executor = mapchete_execute(
            config=mp_config, process_area=box(3, 1, 4, 2), zoom=11, max_attempts=2
        )
        with pytest.raises(MapcheteProcessException):
            list(executor)
