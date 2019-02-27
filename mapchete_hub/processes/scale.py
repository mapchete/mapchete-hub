import logging
try:
    from mapchete_satellite.exceptions import EmptyStackException
except ImportError:
    from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
import numpy.ma as ma

logger = logging.getLogger(__name__)


def execute(
    mp,
    bands=[1, 2, 3, 4],
    td_resampling="nearest",
    td_matching_method="gdal",
    td_matching_max_zoom=None,
    td_matching_precision=8,
    td_fallback_to_higher_zoom=False,
    max_value=10000.,
    out_values=255.,
):
    """
    Scale mosaic to different value range.

    Inputs:
    -------
    mosaic
        mosaic to be scaled

    Parameters:
    -----------
    bands : list
        List of band indexes.
    td_resampling : str (default: 'nearest')
        Resampling used when reading from mosaic.
    td_matching_method : str ('gdal' or 'min') (default: 'gdal')
        gdal: Uses GDAL's standard method. Here, the target resolution is
            calculated by averaging the extent's pixel sizes over both x and y
            axes. This approach returns a zoom level which may not have the
            best quality but will speed up reading significantly.
        min: Returns the zoom level which matches the minimum resolution of the
            extents four corner pixels. This approach returns the zoom level
            with the best possible quality but with low performance. If the
            tile extent is outside of the destination pyramid, a
            TopologicalError will be raised.
    td_matching_max_zoom : int (optional, default: None)
        If set, it will prevent reading from zoom levels above the maximum.
    td_matching_precision : int (default: 8)
        Round resolutions to n digits before comparing.
    td_fallback_to_higher_zoom : bool (default: False)
        In case no data is found at zoom level, try to read data from higher
        zoom levels. Enabling this setting can lead to many IO requests in
        areas with no data.
    max_value : float
        Upper limit for clipping and scaling (e.g. 10000 for Sentinel-2).
    out_values : float
        Output value range (e.g. 255 for 8 bit).

    Output:
    -------
    np.ndarray
        stretched input bands
    """
    logger.debug("read input mosaic")
    with mp.open(
        "mosaic",
        resampling=td_resampling,
        matching_method=td_matching_method,
        matching_max_zoom=td_matching_max_zoom,
        matching_precision=td_matching_precision,
        fallback_to_higher_zoom=td_fallback_to_higher_zoom,
    ) as mosaic_inp:
        if mosaic_inp.is_empty():
            logger.debug("mosaic empty")
            return "empty"
        try:
            mosaic = mosaic_inp.read(indexes=bands).astype(np.int16)
        except EmptyStackException:
            logger.debug("mosaic empty: EmptyStackException")
            return "empty"
        if mosaic[0].mask.all():
            logger.debug("mosaic empty: all masked")
            return "empty"

    logger.debug("stretch values")
    # (1) normalize array from range [0:max_value] to range [0:1]
    # (2) multiply with out_values to create range [0:out_values]
    # (3) clip to [1:out_values] to avoid rounding errors where band value can
    # accidentally become nodata (0)
    # (4) create masked array with burnt in nodata values and original nodata mask
    return ma.masked_array(
        data=np.where(
            mosaic.mask,
            0,
            np.clip(
                (mosaic.astype("float32") / max_value) * out_values,
                1, out_values
            )
        ),
        mask=mosaic.mask
    )
