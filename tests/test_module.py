import geojson
from mapchete.config import raw_conf_process_pyramid, get_zoom_levels
import os
import pytest
from shapely.geometry import box, shape
from tempfile import NamedTemporaryFile

from mapchete_hub import log
from mapchete_hub.application import process_area_from_config
from mapchete_hub.api import format_as_geojson
from mapchete_hub.commands._execute import mapchete_execute
from mapchete_hub.commands._index import mapchete_index


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TESTDATA_DIR = os.path.join(SCRIPT_DIR, "testdata")


def test_mapchete_index(mp_tmpdir, example_mapchete):
    # full area
    assert len(list(mapchete_index(
        mapchete_config=example_mapchete.dict,
        shapefile=True,
        out_dir=mp_tmpdir
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


def test_mapchete_execute(mp_tmpdir, example_mapchete):
    assert list(mapchete_execute(
        mapchete_config=example_mapchete.dict,
        process_area=box(3, 1, 4, 2),
        zoom=11,
    ))


def test_process_area_from_config(example_mapchete):
    bounds = (3, 1, 4, 2)
    point = (3, 1)
    zoom = 11

    # bounds
    assert process_area_from_config(dict(bounds=bounds)).equals(box(*bounds))

    # wkt
    assert process_area_from_config(
        dict(wkt_geometry=box(*bounds).wkt)
    ).equals(box(*bounds))

    # point
    control_geom = raw_conf_process_pyramid(example_mapchete.dict).tile_from_xy(
        *point,
        zoom=max(get_zoom_levels(
            process_zoom_levels=example_mapchete.dict["zoom_levels"],
            init_zoom_levels=zoom
        ))
    ).bbox
    assert process_area_from_config(
        dict(mapchete_config=example_mapchete.dict, point=point, zoom=zoom)
    ).equals(control_geom)

    # config process bounds
    assert process_area_from_config(
        dict(
            mapchete_config=dict(
                example_mapchete.dict,
                process_bounds=bounds
            )
        )
    ).equals(box(*bounds))

    # raise AttributeError
    with pytest.raises(AttributeError):
        process_area_from_config(dict())


def test_log():
    log.set_log_level("DEBUG")
    with NamedTemporaryFile() as tempfile:
        log.setup_logfile(tempfile.name)


def test_format_as_geojson(response_json):
    # single feature
    gj = geojson.loads(format_as_geojson(response_json))
    for f in gj["features"]:
        assert "state" in f["properties"]
        assert shape(f["geometry"]).is_valid
    # multiple features
    gj = geojson.loads(format_as_geojson([response_json, response_json]))
    for f in gj["features"]:
        assert "state" in f["properties"]
        assert shape(f["geometry"]).is_valid
