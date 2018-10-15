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
    bands=[1, 2, 3],
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
            rgb = np.clip(mosaic.read(indexes=bands) / 16., 0, 255)
        except EmptyStackException:
            return "empty"

    # (2) scale rgb bands to 0 to 1 for filters
    red, green, blue = rgb / 255.

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

    # (5) sharpen image
    if sharpen_output:
        logger.debug("sharpen output")
        enhanced = image_sharpening(enhanced)

    # (4) use original nodata mask and return
    return np.where(rgb.mask, mp.params["output"].nodata, enhanced)


def image_sharpening(src):
    return np.clip(reshape_as_raster(
        Image.fromarray(reshape_as_image(src)).filter(ImageFilter.SHARPEN)
    ), 1, 255)
