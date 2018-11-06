from mapchete.log import user_process_logger
from mapchete_satellite.exceptions import EmptyStackException
import numpy as np
from rio_color import operations

from mapchete_hub import image_filters


logger = user_process_logger("color_correction")


def execute(
    mp,
    bands=[1, 2, 3, 4],
    smooth_water=True,
    ndwi_threshold=0.2,
    red_gamma=1.43,
    green_gamma=1.3,
    blue_gamma=1.13,
    sigmoidal_contrast=8.3,
    sigmoidal_bias=0.4,
    saturation=1.3,
    cc_desert=False,
    des_ndvi_min=-0.1,
    des_ndvi_max=0.1,
    des_ndwi_threshold=0.,
    des_red_gamma=1.43,
    des_green_gamma=1.3,
    des_blue_gamma=1.13,
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
    clip (optional)
        vector data used to clip output

    Parameters
    ----------
    bands : list
        List of band indexes.
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

    # read mosaic
    with mp.open("mosaic") as mosaic:
        try:
            raw = mosaic.read(indexes=bands).astype(np.int16)
            nodata_mask = raw[0].mask
        except EmptyStackException:
            logger.debug("no mosaic data over tile")
            return "empty"

    if smooth_water:
        if len(bands) != 4:
            raise ValueError("smooth_water only works with RGBNir bands")

        red, green, blue, nir = raw
        water_mask = np.where(
            (green - nir) / (green + nir) > ndwi_threshold,
            True,
            False
        ).astype("bool")

    # scale down RGB bands to 8 bit and avoid nodata through interpolation
    rgb = np.clip(raw[:3] / 16, 1, 255).astype(np.uint8)

    # smooth out water areas
    if smooth_water and water_mask.any():
        logger.debug("smooth water areas")
        rgb = np.where(
            water_mask,
            image_filters.gaussian_blur(image_filters.smooth(rgb), radius=1),
            rgb
        )

    # sharpen output image
    if sharpen_output:
        if smooth_water and not water_mask.all():
            logger.debug("sharpen output")
            rgb = np.where(
                water_mask,
                rgb,
                image_filters.sharpen(rgb)
                # image_filters.unsharp_mask(
                #     rgb, radius=2, percent=80, threshold=2
                # )
            )
        else:
            rgb = image_filters.sharpen(rgb)

    # apply color correction
    corrected = color_correct(
        rgb=rgb,
        red_gamma=red_gamma,
        green_gamma=green_gamma,
        blue_gamma=blue_gamma,
        sigmoidal_contrast=sigmoidal_contrast,
        sigmoidal_bias=sigmoidal_bias,
        saturation=saturation
    )

    # apply color correction to vegetated areas and merge with corrected
    if cc_desert:
        if len(bands) != 4:
            raise ValueError(
                "desert color correction only works with RGBNir bands"
            )

        red, green, blue, nir = raw
        ndvi = (nir - red) / (nir + red)
        ndwi = (green - nir) / (green + nir)
        desert_mask = np.where(
            (
                (ndvi > des_ndvi_min) &
                (ndvi < des_ndvi_max) &
                (ndwi < des_ndwi_threshold)
            ),
            True,
            False
        ).astype("bool")
        if desert_mask.any():
            logger.debug("apply other color correction for desert areas")
            corrected = np.where(
                desert_mask,
                color_correct(
                    rgb=rgb,
                    red_gamma=des_red_gamma,
                    green_gamma=des_green_gamma,
                    blue_gamma=des_blue_gamma,
                    sigmoidal_contrast=des_sigmoidal_contrast,
                    sigmoidal_bias=des_sigmoidal_bias,
                    saturation=des_saturation
                ),
                corrected
            )

    if clip_geom:
        # apply original nodata mask and clip
        clipped = mp.clip(
            np.where(nodata_mask, mp.params["output"].nodata, corrected),
            clip_geom,
            clip_pixelbuffer=clip_pixelbuffer,
            inverted=True
        )
        return np.where(clipped.mask, clipped, mp.params["output"].nodata)
    else:
        return np.where(nodata_mask, mp.params["output"].nodata, corrected)


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
    ).astype("uint8")
