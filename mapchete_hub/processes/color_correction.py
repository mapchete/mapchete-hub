"""This process extracts cloudless pixels from a time series."""

from mapchete.log import user_process_logger
from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
from rio_color import operations

from mapchete_hub import image_filters


logger = user_process_logger("color_correction")


def execute(
    mp,
    bands=[1, 2, 3, 4],
    smooth_water=True,
    ndwi_threshold=0.65,
    red_gamma=1.43,
    green_gamma=1.3,
    blue_gamma=1.13,
    sigmoidal_contrast=8.3,
    sigmoidal_bias=0.4,
    saturation=1.3,
    cc_vegetation=False,
    ndvi_threshold=0.6,
    veg_red_gamma=1.43,
    veg_green_gamma=1.3,
    veg_blue_gamma=1.13,
    veg_sigmoidal_contrast=8.3,
    veg_sigmoidal_bias=0.4,
    veg_saturation=1.3,
    sharpen_output=False,
    **kwargs
):
    """Extract color-corrected, cloud-free image from Sentinel-2 mosaic."""

    # (1) read mosaic
    with mp.open("mosaic") as mosaic:
        try:
            raw = mosaic.read(indexes=bands).astype(np.int16)
            nodata_mask = raw[0].mask
        except EmptyStackException:
            return "empty"

    if smooth_water:
        if len(bands) != 4:
            raise ValueError("smooth_water only works with RGBNir bands")

        red, green, blue, nir = raw
        water_mask = np.where(
            (green - nir) / (green + nir) < ndwi_threshold,
            True,
            False
        ).astype("bool")

    # (2) apply color correction
    corrected = color_correct(
        rgb=raw[:3],
        red_gamma=red_gamma,
        green_gamma=green_gamma,
        blue_gamma=blue_gamma,
        sigmoidal_contrast=sigmoidal_contrast,
        sigmoidal_bias=sigmoidal_bias,
        saturation=saturation
    )

    # (3) apply color correction to vegetated areas and merge with corrected
    if cc_vegetation:
        if len(bands) != 4:
            raise ValueError("vegetation color correction only works with RGBNir bands")

        red, green, blue, nir = raw
        corrected = np.where(
            # vegetation mask
            np.where(
                (nir - red) / (nir + red) > ndvi_threshold,
                True,
                False
            ).astype("bool"),
            # color correctioin using vegetation values
            color_correct(
                rgb=raw[:3],
                red_gamma=veg_red_gamma,
                green_gamma=veg_green_gamma,
                blue_gamma=veg_blue_gamma,
                sigmoidal_contrast=veg_sigmoidal_contrast,
                sigmoidal_bias=veg_sigmoidal_bias,
                saturation=veg_saturation
            ),
            corrected
        )

    # (4) sharpen image and smooth out water areas
    if smooth_water and water_mask.any():
        logger.debug("smooth water areas")
        corrected = np.where(
            water_mask,
            image_filters.smooth(corrected),
            corrected
        )

    # (5) sharpen output image
    if sharpen_output:
        logger.debug("sharpen output")
        if smooth_water and water_mask.any():
            corrected = np.where(
                water_mask,
                corrected,
                image_filters.sharpen(corrected)
            )
        else:
            corrected = image_filters.sharpen(corrected)

    # (6) use original nodata mask and return
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
    red, green, blue = np.clip(rgb / 16, 0, 255) / 255.
    # color correction using rio-color
    return np.clip(
        operations.saturation(         # add saturation
            operations.sigmoidal(      # add sigmoidal contrast & bias
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
