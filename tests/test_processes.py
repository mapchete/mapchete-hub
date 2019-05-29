import mapchete
from mapchete import MapcheteProcess
import pytest

from mapchete_hub import get_next_jobs
from mapchete_hub.processes import extract_mosaic


def test_submit(example_config):
    jobs = get_next_jobs(
        job_id="first_job",
        config=example_config,
        process_area=None,
    )
    assert len(jobs) == 1


def test_s1_gamma0_mosaic(mundi_example_mapchete_gamma0):
    zoom = 13
    with mapchete.open(mundi_example_mapchete_gamma0) as mp:
        process_tile = next(mp.get_process_tiles(zoom))
        process = MapcheteProcess(config=mp.config, tile=process_tile)

        def _run_with_params(**kwargs):
            return extract_mosaic.execute(
                process, **dict(mp.config.params_at_zoom(zoom), **kwargs)
            )

        # default run
        assert _run_with_params().any()

        # extraction methods
        with pytest.raises(ValueError):
            _run_with_params(method="invalid")

        # raise exception when using add_indexes with wrong method
        with pytest.raises(ValueError):
            _run_with_params(method="weighted_avg", add_indexes=True)

        # empty stack
        process_tile = mp.config.process_pyramid.tile(13, 1, 1)
        process = MapcheteProcess(config=mp.config, tile=process_tile)
        assert extract_mosaic.execute(
            process, **mp.config.params_at_zoom(zoom)
        ) == "empty"


def test_extract_mosaic(aws_example_mapchete_cm_4b):
    zoom = 13
    with mapchete.open(aws_example_mapchete_cm_4b) as mp:
        process_tile = next(mp.get_process_tiles(zoom))
        process = MapcheteProcess(config=mp.config, tile=process_tile)

        def _run_with_params(**kwargs):
            return extract_mosaic.execute(
                process, **dict(mp.config.params_at_zoom(zoom), **kwargs)
            )

        # default run
        assert _run_with_params().any()

        # extraction methods
        for method in ["ndvi_linreg", "weighted_avg", "max_ndvi"]:
            assert _run_with_params(method=method).any()
        with pytest.raises(ValueError):
            _run_with_params(method="invalid")

        # raise exception when using add_indexes with wrong method
        with pytest.raises(ValueError):
            _run_with_params(method="weighted_avg", add_indexes=True)

        # make sure deprecated "min_stack_height" still works
        assert _run_with_params(min_stack_height=5).any()
        assert _run_with_params(min_stack_height=10).any()

        # masks
        assert _run_with_params(mask_white_areas=True).any()

        # sharpen output
        assert _run_with_params(sharpen_output=True).any()

        # indexes
        assert isinstance(_run_with_params(add_indexes=True, average_over=0), tuple)
        assert isinstance(
            _run_with_params(sharpen_output=True, add_indexes=True, average_over=0), tuple
        )

        # empty stack
        process_tile = mp.config.process_pyramid.tile(13, 1, 1)
        process = MapcheteProcess(config=mp.config, tile=process_tile)
        assert extract_mosaic.execute(
            process, **mp.config.params_at_zoom(zoom)
        ) == "empty"


def test_extract_mosaic_secondary_cube(aws_example_mapchete_cm_4b):
    zoom = 13
    with mapchete.open(
        dict(
            aws_example_mapchete_cm_4b,
            input=dict(
                primary=aws_example_mapchete_cm_4b["input"]["primary"],
                secondary=aws_example_mapchete_cm_4b["input"]["primary"]
            )
        )
    ) as mp:
        assert extract_mosaic.execute(
            MapcheteProcess(config=mp.config, tile=next(mp.get_process_tiles(zoom))),
            **mp.config.params_at_zoom(zoom)
        ).any()


def test_extract_mosaic_clip(
    aws_example_mapchete_cm_4b, landpoly_geojson, tile_13_1986_8557_geojson
):
    zoom = 13
    with mapchete.open(
        dict(
            aws_example_mapchete_cm_4b,
            input=dict(
                primary=aws_example_mapchete_cm_4b["input"]["primary"],
                clip=landpoly_geojson
            )
        )
    ) as mp:
        assert extract_mosaic.execute(
            MapcheteProcess(config=mp.config, tile=next(mp.get_process_tiles(zoom))),
            **mp.config.params_at_zoom(zoom)
        ) == "empty"

    with mapchete.open(
        dict(
            aws_example_mapchete_cm_4b,
            input=dict(
                primary=aws_example_mapchete_cm_4b["input"]["primary"],
                clip=tile_13_1986_8557_geojson
            )
        )
    ) as mp:
        assert extract_mosaic.execute(
            MapcheteProcess(config=mp.config, tile=next(mp.get_process_tiles(zoom))),
            **mp.config.params_at_zoom(zoom)
        ).any()
