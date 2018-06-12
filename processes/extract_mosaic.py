"""Extract mosaics by the brightness."""

from mapchete.log import user_process_logger
from mapchete_s2aws.exceptions import EmptyStackException
from orgonite import cloudless

logger = user_process_logger("extract_mosaic")


def execute(
    mp,
    bands,
    resampling="nearest",
    mask_clouds=True,
    mask_white_areas=True,
    read_threads=2,
    timeout=600,
    average_over=3
):
    with mp.open("s2") as src:
        try:
            return cloudless.from_brightness(
                src.read(
                    indexes=bands,
                    resampling=resampling,
                    mask_clouds=mask_clouds,
                    mask_white_areas=mask_white_areas,
                    threads=read_threads,
                    timeout=timeout
                ),
                average_over=average_over
            )
        except EmptyStackException:
            return "empty"
