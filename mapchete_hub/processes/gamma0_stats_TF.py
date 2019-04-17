import numpy as np
import os

from mapchete import Timer
from mapchete_satellite.exceptions import EmptyStackException
from mapchete.log import driver_logger

logger = driver_logger("mapchete.execute")


def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]


# the outlier removal, needs revision (e.g. use something profound)
def outlier_removal(arrayin, threshold=10):
    # remove 0 values
    valid = np.where(arrayin != 0, True, False)
    arrayin = np.ma.MaskedArray(
        arrayin,
        mask=valid
    )

    # calculate percentiles
    p95 = np.percentile(arrayin, 95, axis=0)
    p5 = np.percentile(arrayin, 5, axis=0)

    # we mask out the percetile outliers for std dev calculation
    masked_array = np.ma.MaskedArray(
        arrayin,
        mask=np.logical_or(
            arrayin > p95,
            arrayin < p5
        )
    )
    # we calculate new std and mean
    masked_std = np.std(masked_array, axis=0)
    masked_mean = np.mean(masked_array, axis=0)

    # we mask based on mean +- 3 * stddev
    array_out = np.ma.MaskedArray(
        arrayin,
        mask=np.logical_or(
            arrayin > masked_mean + masked_std * 2,
            arrayin < masked_mean - masked_std * 2,
            )
    )
    # Use a threshhold to filter out values, 10 db difference default
    out = None
    masked_mean = np.mean(array_out, axis=0)
    for s in array_out:
        dif_array = np.where(abs(abs(masked_mean)-abs(s)) > threshold, True, False)
        if out is None:
            out = np.ma.MaskedArray(
                s,
                mask=dif_array
            )
        else:
            out = np.concatenate((out, np.ma.MaskedArray(s, mask=dif_array)), axis=0)

    return out


def execute(
        mp
):
    primary = mp.open("primary")
    try:
        # read stack
        stack = primary.read(indexes=[1, 2], resampling='Cubic Convolution')
    except EmptyStackException:
        return "empty"

    if stack is None:
        return "empty"
    with Timer() as t:
        with np.errstate(all='ignore'):
            vv_stack_db = np.where((
                   stack.data[:, 0, :, :] != 0) & (stack.data[:, 0, :, :] > 0.0005),
                   10*np.log10(stack.data[:, 0, :, :]), 0
                                   )
            vh_stack_db = np.where((
                       stack.data[:, 1, :, :] != 0) & (stack.data[:, 1, :, :] > 0.0005),
                       10*np.log10(stack.data[:, 1, :, :]), 0
                                   )

            vv_stack_db = outlier_removal(vv_stack_db,
                                          threshold=10).reshape(vv_stack_db.shape)
            vh_stack_db = outlier_removal(vh_stack_db,
                                          threshold=10).reshape(vh_stack_db.shape)

            vv_stack_db = np.ma.masked_equal(vv_stack_db, 0.0, copy=False)
            vh_stack_db = np.ma.masked_equal(vh_stack_db, 0.0, copy=False)

            avg_vv = np.mean(vv_stack_db, axis=0)
            avg_vh = np.mean(vh_stack_db, axis=0)

            min_vv = np.min(vv_stack_db, axis=0)
            min_vh = np.min(vh_stack_db, axis=0)

            max_vv = np.max(vv_stack_db, axis=0)
            max_vh = np.max(vh_stack_db, axis=0)

            stddev_vv = np.std(vv_stack_db, axis=0)
            stddev_vh = np.std(vh_stack_db, axis=0)

            count = np.count_nonzero(vh_stack_db, axis=0)

            mosaic = np.stack([avg_vv, avg_vh, min_vv, min_vh, max_vv, max_vh,
                               stddev_vv, stddev_vh, count])
    logger.debug("extracted in %s", t)
    return mosaic
