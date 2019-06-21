import json
import logging
import numpy as np
from numpy import ma

from mapchete import Timer
from orgonite import cloudless

from scipy.ndimage.filters import uniform_filter
from scipy.ndimage.measurements import variance

from mapchete_satellite.exceptions import EmptyStackException

logger = logging.getLogger(__name__)


def _burn_mask(stack, nodata):
    """Burn nodata values into stack."""
    if isinstance(stack, ma.MaskedArray):
        stack.set_fill_value(nodata)
        return stack.filled()
    return stack


def gen_slice_indexes(stack_height, nodata=0):
    """Returns slice indexes and skip nodata value."""
    offset = 0
    for i in range(stack_height):
        if i == nodata:
            offset += 1
        yield i + offset


def _prepare_stack(stack, nodata=0, keep_slice_indexes=False):
    """
    Prepare stack for processing.

    Burn nodata value into stack if stack is a masked array and append a slice index
    band if required.
    """
    if keep_slice_indexes:
        return np.stack([
            # add index band with slice ID to each slice
            np.concatenate((
                slice_,
                # index band
                np.expand_dims(
                    # create band with nodata or slice_id values
                    np.where((slice_ == nodata).sum(axis=0), nodata, slice_id),
                    axis=0
                )
            ))
            for slice_id, slice_ in zip(
                gen_slice_indexes(stack.shape[0], nodata), _burn_mask(stack, nodata)
            )
        ]).astype(np.dtype("int_"), copy=False)
    else:
        return _burn_mask(stack, nodata).astype(np.dtype("int_"), copy=False)


def lee_filter(img, size):
    img_mean = uniform_filter(img, (size, size))
    img_sqr_mean = uniform_filter(img**2, (size, size))
    img_variance = img_sqr_mean - img_mean**2

    overall_variance = variance(img)

    img_weights = img_variance / (img_variance + overall_variance)
    img_output = img_mean + img_weights * (img - img_mean)
    return img_output


def execute(
        mp,
        bands=1,
        resampling="cubic_spline",
        add_indexes=False,
        read_threads=1,
        **kwargs
):
    # read stack
    with mp.open("s1") as s1_cube:
        if s1_cube.is_empty():
            return "empty"
        try:
            stack = s1_cube.read_cube(indexes=bands, resampling=resampling)
        except EmptyStackException:
            return 'empty'

        _stack = _prepare_stack(
            stack.data*10000,
            keep_slice_indexes=add_indexes
        ).astype(np.float32, copy=False)

        mosaic = np.full(mp.tile.shape, 25000)
        for s in _stack:
            s = np.floor(s)
            mosaic = np.where((s[0] < mosaic) & (s[0] > 0.0) & (s[0] < 10000),
                              s,
                              mosaic
                              ).astype(np.uint16, copy=False)
        mosaic = np.where(mosaic == 25000, 0, mosaic)

        # optional index band
        if add_indexes:
            logger.debug("generate tags")
            tags = {
                s_id: dict(timestamp=str(s.timestamp), datastrip_id=s.slice_id)
                for s_id, s in zip(
                    cloudless.gen_slice_indexes(
                        len(stack.data), nodata=0
                    ),
                    stack
                )
            }
            return mosaic, {'datasets': json.dumps(tags)}
        else:
            return mosaic
