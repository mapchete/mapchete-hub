import json
from functools import partial
import logging
from mapchete import Timer
from mapchete_satellite.exceptions import EmptyStackException
from mapchete_satellite.masks import white, s2_landmask, s2_vegetationmask, s2_shadowmask, s2_cloudmask, s2_inverted_landmask
from mapchete_satellite import masks
from mapchete_satellite.utils import read_leveled_cubes
import numpy as np
from orgonite import cloudless
import warnings

from mapchete_hub import image_filters


logger = logging.getLogger(__name__)


def scl_shadow_mask(scl=None, water_buffer=0, vegetation_buffer=0, buffer=0):
    # mask = np.where(
    #     masks.scl_water(scl=scl, buffer=water_buffer) | masks.scl_vegetation(scl=scl, buffer=vegetation_buffer),
    #     False,
    #     masks.scl_cloud_shadows(scl=scl,buffer=buffer)
    # ).astype(np.bool)
    return masks.buffer_array(masks.scl_cloud_shadows(scl=scl), buffer)


def execute(
    mp,
    bands=None,
    resampling="cubic_spline",
    stack_target_height=10,
    mask_clouds=True,
    clouds_buffer=0,
    mask_white_areas=False,
    mask_s2_land=False,
    mask_s2_vegetation=False,
    read_threads=1,
    add_indexes=False,
    method="brightness",
    considered_bands=4,
    average_over=3,
    simulation_value=1.25,
    value_range_min=1500,
    value_range_max=1800,
    value_range_weight=3,
    core_value_range_min=700,
    core_value_range_max=1500,
    core_value_range_weight=8,
    min_stack_height=10,
    input_values_threshold_multiplier=10,
    sharpen_output=False,
    clip_pixelbuffer=0,
    **kwargs
):
    """
    Extract cloudless mosaic from time series.

    Inputs:
    -------
    primary
        S2AWS or S2Mundi time series cube
    secondary (optional)
        S2AWS or S2Mundi time series cube
    clip (optional)
        vector data used to clip output

    Parameters:
    -----------
    bands : list
        List of band indexes. Depending on extraction method, at least RGB or RGBNir bands
        are required.
    resampling : bool
        Resampling method used for input data. (default: "cubic_spline")
    stack_target_height : int
        Read until all pixels in stack have height n. (default: 10)
    mask_clouds : bool
        Mask out clouds from input data. (default: True)
    clouds_buffer : int
        Apply buffer of n pixels to cloud masks. (default: 0)
    mask_white_areas : bool
        Mask out white areas. (default: False)
    mask_s2_land : bool
        Prefer land masked input pixels. (default: False)
    mask_s2_vegetation : bool
        Prefer vegetation masked input pixels. (default: False)
    read_threads : int
        Use threads to read input slices concurrently. (default: 1)
    add_indexes : bool
        Add slice indexes to output. (default: False)
    method : string
        Method to use when extracting mosaic. (default: "brightness")
        Available methods:
            - brightness
            - ndvi_linreg
            - weighted_avg
            - max_ndvi
    considered_bands : bool
        Use first n bands to determine pixel brightness. (brightness method; default: 4)
    average_over : int
        Average over n pixels on time stack. (brightness or max_ndvi method; default: 3)
    simulation_value : float
        NDVI simulation value. (ndvi_linreg method; default: 1.25)
    value_range_min : int
        Value range minimum. (ndvi_linreg and weighted_avg methods; default: 1500)
    value_range_max : int
        Value range minimum. (ndvi_linreg and weighted_avg methods; default: 1800)
    value_range_weight : int
        Value range weight. (ndvi_linreg and weighted_avg methods; default: 3)
    core_value_range_min : int
        Core value range minimum. (ndvi_linreg and weighted_avg methods; default: 700)
    core_value_range_max : int
        Core value range minimum. (ndvi_linreg and weighted_avg methods; default: 1500)
    core_value_range_weight : int
        Core value range weight. (ndvi_linreg and weighted_avg methods; default: 8)
    input_values_threshold_multiplier : int
        Threshold multiplier. (weighted_avg method; default: 10)
    sharpen_output : bool
        Apply sharpening filter on output. (default: False)

    Output:
    -------
    np.ndarray
        input bands + optional index band
    """
    if method not in ["brightness", "ndvi_linreg", "weighted_avg", "max_ndvi"]:
        raise ValueError("invalid extraction method given")
    if add_indexes and method not in ["brightness", "max_ndvi"]:
        raise ValueError(
            "add_indexes option only works with 'brigtness' or 'max_ndvi' extraction "
            "methods"
        )
    if min_stack_height != 10:
        warnings.warn(
            DeprecationWarning(
                "min_stack_height is deprecated and will be replaced by "
                "stack_target_height"
            )
        )
        if stack_target_height == 10:
            stack_target_height = min_stack_height

    # read clip geometry
    if "clip" in mp.params["input"]:
        clip_geom = mp.open("clip").read()
        if not clip_geom:
            logger.debug("no clip data over tile")
            return "empty"
    else:
        clip_geom = []

    # read stack
    with Timer() as t:
        primary = mp.open("primary")
        level = primary.processing_level.lower()

        if mask_white_areas and level == 'l2a':
            custom_masks_both=(partial(white), partial(scl_shadow_mask, buffer=50))
            custom_masks_white=(partial(white), )
        elif mask_white_areas:
            custom_masks_both = None
            custom_masks_white=(partial(white), )
        else:
            custom_masks_both = None
            custom_masks_white = None

        if "secondary" in mp.params["input"]:
                    secondary = mp.open("secondary")
                    cubes = (primary, secondary)
                    slice_ids = (
                        primary.sorted_slice_ids("time_difference"),
                        secondary.sorted_slice_ids("time_difference")
                    )
        else:
            cubes = (primary, )
            slice_ids = (primary.sorted_slice_ids("time_difference"), )
        try:
            stack = read_leveled_cubes(
                cubes,
                slice_ids,
                indexes=bands,
                target_height=stack_target_height,
                resampling=resampling,
                mask_clouds=mask_clouds,
                clouds_buffer=350,
                custom_masks=custom_masks_white
            )
        except EmptyStackException:
            return "empty"

    logger.debug("read %s slices", len(stack.data))
    logger.debug("stack read in %s", t)

    # Basic Mosaic
    mosaic = _extract_mosaic(
        stack.data,
        method,
        average_over=average_over,
        considered_bands=considered_bands,
        simulation_value=simulation_value,
        value_range_weight=value_range_weight,
        core_value_range_weight=core_value_range_weight,
        value_range_min=value_range_min,
        value_range_max=value_range_max,
        core_value_range_min=core_value_range_min,
        core_value_range_max=core_value_range_max,
        input_values_threshold_multiplier=input_values_threshold_multiplier,
        from_brightness_average_over=average_over,
        keep_slice_indexes=add_indexes,
    )

    if level == 'l2a':
        _stack = read_leveled_cubes(
            cubes,
            slice_ids,
            indexes=bands,
            target_height=stack_target_height,
            resampling=resampling,
            mask_clouds=mask_clouds,
            clouds_buffer=350,
            custom_masks=custom_masks_both
        )
        _mosaic = _extract_mosaic(
                _stack.data,
                method,
                average_over=average_over,
                considered_bands=considered_bands,
                simulation_value=simulation_value,
                value_range_weight=value_range_weight,
                core_value_range_weight=core_value_range_weight,
                value_range_min=value_range_min,
                value_range_max=value_range_max,
                core_value_range_min=core_value_range_min,
                core_value_range_max=core_value_range_max,
                input_values_threshold_multiplier=input_values_threshold_multiplier,
                from_brightness_average_over=average_over,
                keep_slice_indexes=add_indexes,
                )

        mosaic = np.where(_mosaic, _mosaic, mosaic).astype(np.int16)


    # optional sharpen
    if sharpen_output:
        logger.debug("sharpen output")
        if add_indexes:
            mosaic = np.concatenate((
                image_filters.sharpen_16bit(mosaic[:-1]),
                np.expand_dims(mosaic[-1], axis=0)
            ))
        else:
            mosaic = image_filters.sharpen_16bit(mosaic)

    # optional clip
    if clip_geom:
        clipped = mp.clip(
            mosaic,
            clip_geom,
            clip_buffer=clip_pixelbuffer,
            inverted=True
        )
        mosaic = np.where(clipped.mask, clipped, mp.params["output"].nodata)

    # optional index band
    if add_indexes:
        logger.debug("generate tags")
        tags = {
            s_id: dict(timestamp=str(s.timestamp), slice_id=s.slice_id)
            for s_id, s in zip(
                cloudless.gen_slice_indexes(
                    len(stack.data), nodata=mp.params["output"].nodata
                ),
               stack
            )
        }
        return mosaic, {'datasets': json.dumps(tags)}
    else:
        return mosaic


def _extract_mosaic(
    stack_data,
    method,
    average_over=None,
    considered_bands=None,
    simulation_value=None,
    value_range_weight=None,
    core_value_range_weight=None,
    value_range_min=None,
    value_range_max=None,
    core_value_range_min=None,
    core_value_range_max=None,
    input_values_threshold_multiplier=None,
    from_brightness_average_over=None,
    keep_slice_indexes=None,
):
    # extract mosaic
    logger.debug("run orgonite '%s' method", method)
    with Timer() as t:
        if method == "brightness":
            mosaic = cloudless.from_brightness(
                stack_data,
                average_over=average_over,
                considered_bands=considered_bands,
                keep_slice_indexes=keep_slice_indexes,
            )
        elif method == "ndvi_linreg":
            mosaic = cloudless.ndvi_linreg(
                stack_data,
                simulation_value=simulation_value,
                value_range_weight=value_range_weight,
                core_value_range_weight=core_value_range_weight,
                value_range_min=value_range_min,
                value_range_max=value_range_max,
                core_value_range_min=core_value_range_min,
                core_value_range_max=core_value_range_max
            )
        elif method == "weighted_avg":
            mosaic = cloudless.weighted_avg(
                stack_data,
                value_range_min=value_range_min,
                value_range_max=value_range_max,
                value_range_weight=value_range_weight,
                core_value_range_min=core_value_range_min,
                core_value_range_max=core_value_range_max,
                core_value_range_weight=core_value_range_weight,
                input_values_threshold_multiplier=input_values_threshold_multiplier
            )
        elif method == "max_ndvi":
            mosaic = cloudless.max_ndvi(
                stack_data,
                min_ndvi=0.2,
                max_ndvi=0.95,
                from_brightness_average_over=average_over,
                keep_slice_indexes=keep_slice_indexes
            )
    logger.debug("extracted in %s", t)
    return mosaic
