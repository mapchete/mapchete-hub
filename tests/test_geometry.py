import pytest
from mapchete.config.parse import raw_conf_process_pyramid
from shapely.geometry import box, mapping, shape

from mapchete_hub import models
from mapchete_hub.geometry import process_area_from_config


def test_process_area_from_config_bounds(example_config_json):
    bounds = (3, 1, 4, 2)
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(bounds=bounds))
    )
    assert shape(process_area_from_config(job_config)[0]).equals(box(*bounds))


def test_process_area_from_config_bounds_and_area(example_config_json):
    bounds = (3, 1, 4, 2)
    area = box(3.5, 1.5, 4.5, 2.5)
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(bounds=bounds, area=area.wkt))
    )
    assert shape(process_area_from_config(job_config)[0]).equals(
        box(*bounds).intersection(area)
    )


def test_process_area_from_config_geometry(example_config_json):
    bounds = (3, 1, 4, 2)
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(geometry=mapping(box(*bounds))))
    )
    assert shape(process_area_from_config(job_config)[0]).equals(box(*bounds))


def test_process_area_from_config_point(example_config_json):
    point = (3, 1)
    zoom = 11

    # point
    control_geom = (
        raw_conf_process_pyramid(example_config_json["config"])
        .tile_from_xy(*point, zoom)
        .bbox
    )
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(point=point, zoom=zoom))
    )
    assert shape(process_area_from_config(job_config)[0]).buffer(0).equals(control_geom)


def test_process_area_from_config_tile(example_config_json):
    point = (3, 1)
    zoom = 11
    control_geom = (
        raw_conf_process_pyramid(example_config_json["config"])
        .tile_from_xy(*point, zoom)
        .bbox
    )

    # tile
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(tile=(11, 506, 1041), zoom=zoom))
    )
    area = shape(process_area_from_config(job_config)[0]).buffer(0)
    assert area.equals(control_geom)


def test_process_area_from_config_process_bounds(example_config_json):
    bounds = (3, 1, 4, 2)

    # config process bounds
    job_config = models.MapcheteJob(
        **dict(
            example_config_json,
            config=dict(example_config_json["config"], bounds=bounds),
            params=dict(zoom=8),
        )
    )
    area = shape(process_area_from_config(job_config)[0]).buffer(0)
    assert area.equals(box(*bounds))


def test_process_area_from_config_errors(example_config_json):
    # errors
    with pytest.raises(TypeError):
        process_area_from_config(job_config=None)
    with pytest.raises(TypeError):
        process_area_from_config(job_config=dict())
    with pytest.raises(TypeError):
        process_area_from_config(job_config=dict(config=example_config_json["config"]))
