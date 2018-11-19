import json
from mapchete import Timer
from mapchete.log import user_process_logger
try:
    from mapchete_satellite.exceptions import EmptyStackException
except ImportError:
    from mapchete_s2aws.exceptions import EmptyStackException
try:
    from mapchete_satellite.utils import read_leveled_cubes
except ImportError:
    from mapchete_s2aws import read_min_cubes as read_leveled_cubes
import numpy as np
from orgonite import cloudless

from mapchete_hub import image_filters


logger = user_process_logger("extract_mosaic")


def execute(
    mp,
    bands=None,
    resampling="cubic_spline",
    stack_target_height=10,
    mask_clouds=True,
    cloudmask_types="all",
    mask_white_areas=False,
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
    sharpen_output=True,
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
    cloudmask_types : string
        Use certain cloud mask types only. (default: "all")
    mask_white_areas : bool
        Mask out white areas. (default: False)
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
        Average over n pixels on time stack. (brightness method; default: 3)
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
        Apply sharpening filter on output. (default: True)

    Output:
    -------
    np.ndarray
        input bands + optional index band
    """
    if method not in ["brightness", "ndvi_linreg", "weighted_avg", "max_ndvi"]:
        raise ValueError("invalid extraction method given")
    if add_indexes and method != "brightness":
        raise ValueError(
            "add_indexes option only works with 'brigtness' extraction method"
        )
    if min_stack_height != 10:
        raise DeprecationWarning(
            "min_stack_height is deprecated and will be replaced by stack_target_height"
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
        if "secondary" in mp.params["input"]:
            secondary = mp.open("secondary")
            cubes = (primary, secondary)
            datastrip_ids = (
                primary.sorted_datastrip_ids("time_difference"),
                secondary.sorted_datastrip_ids("time_difference")
            )
        else:
            cubes = (primary, )
            datastrip_ids = (primary.sorted_datastrip_ids("time_difference"), )
        try:
            stack = read_leveled_cubes(
                cubes,
                datastrip_ids,
                indexes=bands,
                min_height=min_stack_height,
                resampling=resampling,
                mask_clouds=mask_clouds,
                cloudmask_types=(
                    tuple(cloudmask_types)
                    if isinstance(cloudmask_types, list) else cloudmask_types
                ),
                mask_white_areas=mask_white_areas
            )
        except EmptyStackException:
            return "empty"

    logger.debug("read %s slices", len(stack.data))
    logger.debug("stack read in %s", t)

    # extract mosaic
    logger.debug("extract mosaic")
    with Timer() as t:
        if method == "brightness":
            mosaic = cloudless.from_brightness(
                stack.data,
                average_over=average_over,
                considered_bands=considered_bands,
                keep_slice_indexes=add_indexes,
            )
        elif method == "ndvi_linreg":
            mosaic = cloudless.ndvi_linreg(
                stack.data,
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
                stack.data,
                value_range_min=value_range_min,
                value_range_max=value_range_max,
                value_range_weight=value_range_weight,
                core_value_range_min=core_value_range_min,
                core_value_range_max=core_value_range_max,
                core_value_range_weight=core_value_range_weight,
                input_values_threshold_multiplier=input_values_threshold_multiplier
            )
        elif method == "max_ndvi":
            mosaic = cloudless.max_ndvi(stack.data)
    logger.debug("extracted in %s", t)
    logger.debug("mosaic shape: %s", mosaic.shape)

    # optional sharpen
    if sharpen_output:
        logger.debug("sharpen output")
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
            s_id: dict(timestamp=s.timestamp, datastrip_id=s.datastrip_id)
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
