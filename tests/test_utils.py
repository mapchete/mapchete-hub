import base64
import mapchete
from mapchete.config import raw_conf_process_pyramid
from mapchete.errors import MapcheteProcessImportError
import pytest
from shapely.geometry import box, mapping

from mapchete_hub.api import load_batch_config
from mapchete_hub.utils import (
    custom_process_tempfile,
    parse_jobs_for_backend,
    process_area_from_config
)


def test_process_area_from_config(example_mapchete):
    bounds = (3, 1, 4, 2)
    point = (3, 1)
    zoom = 11

    # bounds
    assert process_area_from_config(
        config=example_mapchete.dict,
        params=dict(bounds=bounds)
    )[0].equals(box(*bounds))

    # geometry
    assert process_area_from_config(
        config=example_mapchete.dict,
        params=dict(geometry=mapping(box(*bounds)))
    )[0].equals(box(*bounds))

    control_geom = raw_conf_process_pyramid(
        example_mapchete.dict
    ).tile(11, 253, 520).bbox
    # point
    assert process_area_from_config(
        config=example_mapchete.dict,
        params=dict(
            point=point,
            zoom=zoom
        )
    )[0].equals(control_geom)
    # tile
    assert process_area_from_config(
        config=example_mapchete.dict,
        params=dict(
            tile=(11, 253, 520),
            zoom=zoom
        )
    )[0].equals(control_geom)

    # config process bounds
    assert process_area_from_config(
        config=dict(
            example_mapchete.dict,
            process_bounds=bounds
        )
    )[0].equals(box(*bounds))

    # errors
    with pytest.raises(TypeError):
        process_area_from_config(config=None)
    with pytest.raises(KeyError):
        process_area_from_config(config=dict())
    with pytest.raises(AttributeError):
        process_area_from_config(config=example_mapchete.dict)


def test_custom_process_tempfile(example_mapchete):
    process = base64.standard_b64encode("""
def execute(mp):
    return "empty"
        """.encode("utf-8")
    ).decode("utf-8")
    custom_process = dict(
        example_mapchete.dict,
        process=process
    )
    with custom_process_tempfile(custom_process) as config:
        assert config.get("process").endswith(".py")
        with mapchete.open(config):
            pass

    custom_process.pop("process")
    with pytest.raises(MapcheteProcessImportError):
        with custom_process_tempfile(custom_process) as _:
            pass


def test_parse_jobs_for_backend(batch_example):
    jobs = parse_jobs_for_backend(
        load_batch_config(
            batch_example.path,
            bounds=[0, 1, 2, 3]
        )["jobs"].values()
    )
    job_id = jobs[0]["kwargs"].get("job_id")
    next_job_id = jobs[0]["kwargs"].get("next_job_id")
    for job in jobs[1:]:
        kwargs = job["kwargs"]
        assert kwargs.get("previous_job_id") == job_id
        assert kwargs.get("job_id") == next_job_id
        next_job_id = kwargs.get("next_job_id")
        job_id = kwargs.get("job_id")
