"""Example process file."""
import time
from random import randint


def execute(mp):
    """User defined process."""
    assert randint(0, 500)
    time.sleep(10 // randint(1, 50))
    return "empty"
    # Reading and writing data works like this:
    # with mp.open("file1", resampling="bilinear") as raster_file:
    #     if raster_file.is_empty():
    #         return "empty"
    #         # This assures a transparent tile instead of a pink error tile
    #         # is returned when using mapchete serve.
    #     dem = raster_file.read()
    # return dem
