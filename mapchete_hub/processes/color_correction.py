"""This process extracts cloudless pixels from a time series."""

from mapchete.log import user_process_logger
from mapchete_s2aws.exceptions import EmptyStackException
import numpy as np
from rio_color.operations import sigmoidal, gamma, saturation


logger = user_process_logger("color_correction")

def execute(mp):
    """Extract color-corrected, cloud-free image from Sentinel-2 timestack."""
    # (1) read mosaic
    with mp.open("mosaic") as mosaic:
        try:
            rgb = np.clip(
                mosaic.read(indexes=mp.params["bands"]) / 16, 0, 255
            )
        except EmptyStackException:
            return "empty"

    # (2) scale rgb bands to 0 to 1 for filters
    red, green, blue = rgb / 255.

    # (3) color correction using rio-color
    enhanced = np.clip(
        saturation(         # add saturation
            sigmoidal(      # add sigmoidal contrast & bias
                np.stack([  # apply gamma correction to each band
                    gamma(red, mp.params["red_gamma"]),
                    gamma(green, mp.params["green_gamma"]),
                    gamma(blue, mp.params["blue_gamma"]),
                ]),
                mp.params["sigmoidal_contrast"],
                mp.params["sigmoidal_bias"]
            ),
            mp.params["saturation"]
        ) * 255,    # scale back to 8bit
        1, 255      # clip valid values to 1 and 255
    ).astype("uint8")

    # (4) use original nodata mask and return
    return np.where(rgb.mask, mp.params["output"].nodata, enhanced)
