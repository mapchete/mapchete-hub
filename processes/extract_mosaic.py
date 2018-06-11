"""Extract mosaics by the brightness."""

from mapchete.log import user_process_logger
from mapchete_s2aws.exceptions import EmptyStackException
from orgonite import cloudless

logger = user_process_logger("extract_mosaic")


def execute(
    mp, bands, resampling, mask_clouds, mask_white_areas, read_threads, average_over
):
    with mp.open("s2") as src:
        try:
            return cloudless.from_brightness(
                src.read(
                    indexes=mp.params["bands"],
                    resampling=mp.params["resampling"],
                    mask_clouds=mp.params["mask_clouds"],
                    mask_white_areas=mp.params["mask_white_areas"],
                    threads=mp.params["read_threads"]
                ),
                average_over=mp.params["average_over"]
            )
        except EmptyStackException:
            return "empty"
