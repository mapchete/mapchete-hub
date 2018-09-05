"""
Template to extract mosaics by various methods.

This process requires Sentinel-2 bands 4, 3, 2 and 8 (in exactly this order) and returns
6 bands:
- red
- green
- blue
- nir
- slice index
- NDVI

Required mapchete parameters:

bands: [4, 3, 2, 8]
resampling: <resampling_method>
mask_clouds: true or false
mask_white_areas: true or false
read_threads: <int>
method: brightness or ndvi
    brightness:
        average_over: 0, 3 or 5
    ndvi:
        min_ndvi: float between -1 and 1
        max_ndvi: float between -1 and 1
"""
import json
from mapchete import Timer
from mapchete.log import user_process_logger
from mapchete_s2aws import read_min_cubes
from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
from orgonite import cloudless
from scipy import ndimage


logger = user_process_logger("extract_mosaic")


def execute(
    mp,
    bands=None,
    resampling="cubic_spline",
    mask_clouds=True,
    mask_white_areas=False,
    read_threads=1,
    add_indexes=False,
    method="brighntess",
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
    **kwargs
):
    if method not in ["brightness", "ndvi_linreg", "weighted_avg", "max_ndvi"]:
        raise ValueError("invalid extraction method given")
    if add_indexes and method != "brightness":
        raise ValueError(
            "add_indexes option only works with 'brigtness' extraction method"
        )

    # read stack
    with Timer() as t:
        primary = mp.open("primary")
        if "secondary" in mp.params["input"]:
            secondary = mp.open("secondary")
            cubes = (primary, secondary)
            datastrip_ids = (
                primary.sorted_datastrip_ids(),
                secondary.sorted_datastrip_ids()
            )
        else:
            cubes = (primary, )
            datastrip_ids = (primary.sorted_datastrip_ids(), )
        try:
            stack = read_min_cubes(
                cubes,
                datastrip_ids,
                indexes=bands,
                min_height=min_stack_height,
                resampling=resampling,
                mask_clouds=mask_clouds,
                mask_white_areas=mask_white_areas
            )
        except EmptyStackException:
            return "empty"

    logger.debug("read %s slices", len(stack.data))
    logger.debug("stack read in %ss", t)

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
    logger.debug("extracted in %ss", t)
    logger.debug("mosaic shape: %s", mosaic.shape)

    if sharpen_output:
        logger.debug("sharpen output")
        mosaic = image_sharpening(mosaic)

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


def get_stack_height(stack):
    return np.sum(np.stack([i.all(axis=0) for i in stack]), axis=0)


def image_sharpening(src):
    """
    kernel_3x3_highpass = np.array([0, -1, 0, -1, 5, -1, 0, -1, 0]).reshape((3, 3))
    kernel_3x3_highpass = np.array([0, -1/4, 0, -1/4, 2, -1/4, 0, -1/4, 0]).reshape((3, 3))
    kernel_5x5_highpass = np.array([0, -1, -1, -1, 0, -1, -2, -4, 2, -1, -1, -4, 13, -4, -1, -1, 2, -4, 2, -1, 0, -1, -1, -1, 0]).reshape((5, 5))

    kernel_mean = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1]).reshape((3, 3))
    kernel = np.array([[1, 1, 1], [1, 1, 0], [1, 0, 0]]).reshape((3, 3))
    kernel = np.array([0, -1, 0, -1, 8, -1, 0, -1, 0]).reshape((3, 3))
    """
    stack = None
    for b in src:
        # Various High Pass Filters
        # b = ndimage.minimum_filter(b, 3)
        # b = ndimage.percentile_filter(b, 50, 3)
        # imgsharp = ndimage.convolve(b_smoothed, kernel_3x3_highpass, mode='nearest')
        # imgsharp = ndimage.median_filter(imgsharp, 2)
        # imgsharp = reshape_as_raster(np.asarray(imgsharp))
        # Official SciPy unsharpen mask filter not working

        # Unshapen Mask Filter, working version as the one above is not working
        b_smoothed = ndimage.percentile_filter(b, 35, 4, mode='nearest')
        mask = b - b_smoothed
        imgsharp = b + mask
        imgsharp = ndimage.percentile_filter(imgsharp, 45, 2, mode='nearest')

        if stack is None:
            stack = np.expand_dims(imgsharp, axis=0).astype(np.uint16)
        else:
            target = np.expand_dims(imgsharp, axis=0).astype(np.uint16)
            stack = np.append(stack, target, axis=0)
    return stack
