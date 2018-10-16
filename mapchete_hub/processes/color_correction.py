"""This process extracts cloudless pixels from a time series."""

from mapchete.log import user_process_logger
from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
from rasterio.plot import reshape_as_raster, reshape_as_image
from PIL import Image, ImageFilter
from rio_color import operations


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
    sharpen_output=False,
    **kwargs
):
    """Extract color-corrected, cloud-free image from Sentinel-2 timestack."""
    # (1) read mosaic
    with mp.open("mosaic") as mosaic:
        try:
            rgbnir = mosaic.read(indexes=bands)
            nodata_mask = rgbnir[0].mask
        except EmptyStackException:
            return "empty"

    if smooth_water:
        if len(bands) != 4:
            raise ValueError("smooth_water only works with RGBNir bands")
        red, green, blue, nir = rgbnir
        water_mask = np.where(
            (green - nir) / (green + nir) < ndwi_threshold,
            True,
            False
        ).astype("bool")

    # (2) scale from 0 to 1 for color correction
    red, green, blue = np.clip(rgbnir[:3] / 16, 0, 255) / 255.

    # (3) color correction using rio-color
    enhanced = np.clip(
        operations.saturation(         # add saturation
            operations.sigmoidal(      # add sigmoidal contrast & bias
                np.stack([  # apply gamma correction to each band
                    operations.gamma(red, red_gamma),
                    operations.gamma(green, green_gamma),
                    operations.gamma(blue, blue_gamma),
                ]),
                sigmoidal_contrast,
                sigmoidal_bias
            ),
            saturation
        ) * 255,    # scale back to 8bit
        1, 255      # clip valid values to 1 and 255 to avoid nodata
    ).astype("uint8")
    enhanced = np.where(nodata_mask, 255, enhanced)

    # (4) sharpen image and smooth out water areas
    if smooth_water and water_mask.any():
        logger.debug("smooth water areas")
        enhanced = np.where(
            water_mask,
            image_smoothing(enhanced),
            enhanced
        )

    # (5) sharpen output image
    if sharpen_output:
        logger.debug("sharpen output")
        if smooth_water and water_mask.any():
            enhanced = np.where(
                water_mask,
                enhanced,
                image_sharpening(enhanced)
            )
        else:
            enhanced = image_sharpening(enhanced)

    # (6) use original nodata mask and return
    return np.where(nodata_mask, mp.params["output"].nodata, enhanced)


def image_sharpening(src):
    return np.clip(reshape_as_raster(
        Image.fromarray(reshape_as_image(src)).filter(ImageFilter.SHARPEN)
    ), 1, 255).astype("uint8")


def image_smoothing(src):
    return np.clip(reshape_as_raster(
        Image.fromarray(reshape_as_image(src)).filter(ImageFilter.SMOOTH_MORE)
    ), 1, 255).astype("uint8")
