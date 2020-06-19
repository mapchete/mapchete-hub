import pytest
from shapely.geometry import box, mapping

from mapchete_hub.commands import execute, index
from mapchete_hub.commands._execute import mapchete_execute
from mapchete_hub.commands._index import mapchete_index
from mapchete_hub.utils import process_area_from_config


@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
def test_index(example_mapchete):
    """Test execution as celery task."""
    # command should fail when no parameters are given
    with pytest.raises(AttributeError):
        index.run.delay().get(propagate=True)

    # full
    params = dict(zoom=7, bounds=[0, 0, 10, 10])
    geom, geom_mhub_crs = process_area_from_config(
        config=example_mapchete.dict, params=params
    )
    index.run.delay(
        params=params,
        config=example_mapchete.dict,
        process_area=mapping(geom_mhub_crs),
        process_area_process_crs=mapping(geom)
    ).get(propagate=True)


def test_index_function(example_mapchete, mp_tmpdir):
    """Test _index function execution."""
    # full
    assert len(list(mapchete_index(
        mapchete_config=example_mapchete.dict,
        shapefile=True,
        out_dir=mp_tmpdir,
        zoom=7
    )))
    # single tile
    assert len(list(mapchete_index(
        mapchete_config=example_mapchete.dict,
        shapefile=True,
        out_dir=mp_tmpdir,
        tile=(11, 244, 517)
    )))

    # test errors
    with pytest.raises(ValueError):
        list(mapchete_index(
            mapchete_config=example_mapchete.dict,
            out_dir=mp_tmpdir
        ))
    with pytest.raises(ValueError):
        list(mapchete_index(
            mapchete_config=example_mapchete.dict,
            shapefile=True,
        ))


@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
def test_execute(example_mapchete, mp_tmpdir):
    """Test execution as celery task."""
    # command should fail when no parameters are given
    with pytest.raises(AttributeError):
        execute.run.delay().get(propagate=True)

    # full
    params = dict(zoom=7, bounds=[-1, -1, 10, 10])
    geom, geom_mhub_crs = process_area_from_config(
        config=example_mapchete.dict, params=params
    )
    execute.run.delay(
        params=params,
        config=example_mapchete.dict,
        process_area=mapping(geom_mhub_crs),
        process_area_process_crs=mapping(geom)
    ).get(propagate=True)


def test_execute_function(mp_tmpdir, example_mapchete):
    """Test _execute function execution."""
    assert list(mapchete_execute(
        mapchete_config=example_mapchete.dict,
        process_area=box(-1, -1, 10, 10),
        zoom=7,
    ))
