import logging
try:
    from mapchete_satellite.exceptions import EmptyStackException
except ImportError:
    from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
from rio_color import operations

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib.colors as colors

from mapchete_satellite.masks import white, buffer_array

logger = logging.getLogger(__name__)


def dark(bands=None, threshold=100, buffer=0):
    return buffer_array(
        np.where(bands < threshold, True, False).all(axis=0).astype(np.bool, copy=False),
        buffer=buffer
    )


def execute(
    mp,
    bands=[1, 2, 3, 4],
    td_resampling="nearest",
    td_matching_method="gdal",
    td_matching_max_zoom=None,
    td_matching_precision=8,
    td_fallback_to_higher_zoom=False,
    white_threshold=4096,
    white_buffer=10,
    dark_threshold=100,
    dark_buffer=10,
    smooth_water=True,
    color_correction=None,
    ndwi_threshold=0.2,
    red_gamma=1.13,
    green_gamma=1.3,
    blue_gamma=1.3,
    sigmoidal_contrast=8.3,
    sigmoidal_bias=0.4,
    saturation=1.3,
    cc_desert=False,
    des_ndvi_min=-0.1,
    des_ndvi_max=0.1,
    des_ndwi_threshold=0.,
    des_red_gamma=1.13,
    des_green_gamma=1.3,
    des_blue_gamma=1.3,
    des_sigmoidal_contrast=8.3,
    des_sigmoidal_bias=0.4,
    des_saturation=1.3,
    sharpen_output=False,
    clip_pixelbuffer=0,
    **kwargs
):
    """
    Extract color-corrected image from Sentinel-2 mosaic.

    Inputs:
    -------
    mosaic
        3 or 4 band 12bit data
    mosaic2
        3 or 4 band 12bit data
        optional backup mosaic in case first mosaic is empty
    clip (optional)
        vector data used to clip output

    Parameters
    ----------
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
    clip_pixelbuffer : int
        Use pixelbuffer when clipping output by geometry. (default: 0)
    smooth_water : bool
        Smooth water areas. (default: True)
    ndwi_threshold : float
        Threshold to determine water areas. (default: 0.2)
    red_gamma : float
        Gamma correction for red band. (default: 1.43)
    green_gamma : float
        Gamma correction for green band. (default: 1.3)
    blue_gamma : float
        Gamma correction for blue band. (default: 1.13)
    sigmoidal_contrast : float
        Sigmoidal contrast. (default: 8.3)
    sigmoidal_bias : float
        Sigmoidal bias. (default: 0.4)
    saturation : float
        Saturation. (default: 1.3)
    cc_desert : bool
        Use different color correction in desert areas. (default: False)
    des_ndvi_min : float
        NDVI minimum threshold to determine desert areas. (default: -0.1)
    des_ndvi_max : float
        NDVI maximum threshold to determine desert areas. (default: 0.1)
    des_ndwi_threshold : float
        NDWI threshold for desert areas. (default: 0.)
    des_red_gamma : float
        Desert area Gamma correction for red band. (default: 1.43)
    des_green_gamma : float
        Desert area Gamma correction for green band. (default: 1.3)
    des_blue_gamma : float
        Desert area Gamma correction for blue band. (default: 1.13)
    des_sigmoidal_contrast : float
        Desert area Sigmoidal contrast. (default: 8.3)
    des_sigmoidal_bias : float
        Desert area Sigmoidal bias. (default: 0.4)
    des_saturation : float
        Desert area Saturation. (default: 1.3)
    sharpen_output : bool
        Apply sharpening filter to output. (default: False)

    Output
    ------
    np.ndarray
        8bit RGB
    """
    # read clip geometry
    if "clip" in mp.params["input"]:
        clip_geom = mp.open("clip").read()
        if not clip_geom:
            logger.debug("no clip data over tile")
            return "empty"
    else:
        clip_geom = []

    # read and merge mosaics
    mosaic, nodata_mask = None, None
    for mosaic_name in ["mosaic_1", "mosaic_2", "mosaic_3",
                        "mosaic_4", "mosaic_5", "mosaic_6",
                        "mosaic_7", "mosaic_8", "mosaic_9",
                        "mosaic_10", "mosaic_11", "mosaic_12"]:
        logger.debug("trying to read from %s", mosaic_name)
        if mosaic_name in mp.params["input"]:
            raw = read_mosaic(
                mp=mp,
                mosaic_name=mosaic_name,
                bands=bands,
                td_matching_method=td_matching_method,
                td_matching_max_zoom=td_matching_max_zoom,
                td_matching_precision=td_matching_precision,
                td_fallback_to_higher_zoom=td_fallback_to_higher_zoom,
                td_resampling=td_resampling
            )
            if isinstance(raw, np.ndarray):
                if mosaic is None:
                    mosaic = raw
                    nodata_mask = raw[0].mask
                else:
                    logger.debug("merging %s with other", mosaic_name)
                    white_mask = white(mosaic,
                                       threshold=white_threshold,
                                       buffer=white_buffer
                                       )
                    dark_mask = dark(mosaic,
                                     threshold=dark_threshold,
                                     buffer=dark_buffer
                                     )
                    mosaic = np.where(
                            ((dark_mask) | (white_mask)) &
                            (np.sum(raw, axis=0) > 250) &
                            (np.sum(raw, axis=0) < 8000),
                            raw, mosaic
                    ).astype(np.int16, copy=False)
                    nodata_mask = np.where(
                        nodata_mask, raw[0].mask, nodata_mask
                    ).astype(np.bool, copy=False)
                if nodata_mask is not None and not nodata_mask.any():
                    logger.debug("tile fully covered")
                    continue
            else:
                logger.debug("%s is empty", mosaic_name)
        else:
            logger.debug("%s is not specified", mosaic_name)
    if nodata_mask is None or nodata_mask.all():
        logger.debug("all mosaics are masked")
        return "empty"

    ndvi = (mosaic[3, :, :]-mosaic[0, :, :])/(mosaic[3, :, :]+mosaic[0, :, :])
    ndvi += 1
    ndwi = (mosaic[1, :, :]-mosaic[3, :, :]) / (mosaic[1, :, :]+mosaic[3, :, :])
    ndvi = np.where(ndwi >= 0.15, 0.7, ndvi)

    cmap = ListedColormap(["white",
                           "royalblue",
                           "grey",
                           "tan",
                           "saddlebrown",
                           "lightgreen",
                           "palegreen",
                           "forestgreen",
                           "darkgreen"
                           ])
    norm = colors.BoundaryNorm([0.0, 0.6, 0.8, 1.2, 1.4, 1.6, 1.8, 2.0], 8)

    my_dpi = 100
    figsize = (mp.tile.shape[0]/my_dpi, mp.tile.shape[1]/my_dpi)
    fig, ax = plt.subplots(figsize=figsize)
    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    ax.imshow(ndvi,
              cmap=cmap,
              norm=norm)
    fig.canvas.draw()

    mosaic = np.array(fig.canvas.renderer._renderer)
    mosaic = np.moveaxis(mosaic, -1, 0)
    mosaic = mosaic[:3, :, :]

    mosaic = np.where(mosaic[0, :, :] == 0, 255, mosaic)

    if clip_geom:
        # apply original nodata mask and clip
        clipped = mp.clip(
            np.where(nodata_mask, mp.params["output"].nodata, mosaic),
            clip_geom,
            clip_buffer=clip_pixelbuffer,
            inverted=True
        )
        return np.where(clipped.mask, clipped, mp.params["output"].nodata)
    else:
        return np.where(nodata_mask, mp.params["output"].nodata, mosaic)


def read_mosaic(
    mp=None,
    mosaic_name=None,
    bands=None,
    td_matching_method=None,
    td_matching_max_zoom=None,
    td_matching_precision=None,
    td_fallback_to_higher_zoom=None,
    td_resampling=None
):
    # read mosaic
    with mp.open(
        mosaic_name,
        matching_method=td_matching_method,
        matching_max_zoom=td_matching_max_zoom,
        matching_precision=td_matching_precision,
        fallback_to_higher_zoom=td_fallback_to_higher_zoom
    ) as mosaic_inp:
        if mosaic_inp.is_empty():
            logger.debug("%s empty", mosaic_name)
            return "empty"
        try:
            mosaic = mosaic_inp.read(
                indexes=bands, resampling=td_resampling
            ).astype(np.int16, copy=False)
        except EmptyStackException:
            logger.debug("%s empty: EmptyStackException", mosaic_name)
            return "empty"
        if mosaic[0].mask.all():
            logger.debug("%s empty: all masked", mosaic_name)
            return "empty"
        return mosaic


def percent_masked(mask=None, nodata_mask=None, round_by=2):
    # divide number of masked and valid pixels by number of valid pixels
    return round(
        100 * np.where(
            nodata_mask, False, mask
        ).sum() / (
            nodata_mask.size - nodata_mask.sum()
        ),
        round_by
    )


def color_correct(
    rgb,
    red_gamma,
    green_gamma,
    blue_gamma,
    sigmoidal_contrast,
    sigmoidal_bias,
    saturation
):
    """
    Return color corrected 8 bit RGB array from 8 bit input RGB.
    """
    red, green, blue = np.clip(rgb, 0, 255) / 255.
    # color correction using rio-color
    return np.clip(
        operations.saturation(          # add saturation
            operations.sigmoidal(       # add sigmoidal contrast & bias
                np.stack([              # apply gamma correction to each band
                    operations.gamma(red, red_gamma),
                    operations.gamma(green, green_gamma),
                    operations.gamma(blue, blue_gamma),
                ]),
                sigmoidal_contrast,
                sigmoidal_bias
            ),
            saturation
        ) * 255,    # scale back to 8bit
        1, 255      # clip valid values to 1 and 255 to avoid accidental nodata values
    ).astype("uint8", copy=False)
