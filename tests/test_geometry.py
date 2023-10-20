from mapchete.config import raw_conf_process_pyramid
import pytest
from shapely.geometry import box, mapping, shape

from mapchete_hub import models
from mapchete_hub.geometry import process_area_from_config


def test_process_area_from_config(example_config_json):
    bounds = (3, 1, 4, 2)
    point = (3, 1)
    zoom = 11

    # bounds
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(bounds=bounds))
    )
    assert shape(process_area_from_config(job_config)[0]).equals(box(*bounds))

    # geometry
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(geometry=mapping(box(*bounds))))
    )
    assert shape(process_area_from_config(job_config)[0]).equals(box(*bounds))

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

    # tile
    job_config = models.MapcheteJob(
        **dict(example_config_json, params=dict(tile=(11, 506, 1041), zoom=zoom))
    )
    area = shape(process_area_from_config(job_config)[0]).buffer(0)
    assert area.equals(control_geom)

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

    # errors
    with pytest.raises(TypeError):
        process_area_from_config(job_config=None)
    with pytest.raises(TypeError):
        process_area_from_config(job_config=dict())
    with pytest.raises(TypeError):
        process_area_from_config(job_config=dict(config=example_config_json["config"]))
