import numpy as np
from rasterio.plot import reshape_as_raster, reshape_as_image
from PIL import Image, ImageFilter


FILTERS = {
    "blur": ImageFilter.BLUR,
    "contour": ImageFilter.CONTOUR,
    "detail": ImageFilter.DETAIL,
    "edge_enhance": ImageFilter.EDGE_ENHANCE,
    "edge_enhance_more": ImageFilter.EDGE_ENHANCE_MORE,
    "emboss": ImageFilter.EMBOSS,
    "find_edges": ImageFilter.FIND_EDGES,
    "sharpen": ImageFilter.SHARPEN,
    "smooth": ImageFilter.SMOOTH,
    "smooth_more": ImageFilter.SMOOTH_MORE,
}


def _apply_filter(arr, img_filter):
    if arr.dtype != "uint8":
        raise TypeError("input array type must be uint8")
    if arr.ndim != 3:
        raise TypeError("input array must be 3-dimensional")
    if arr.shape[0] != 3:
        raise TypeError("input array must have exactly three bands")
    return np.clip(
        reshape_as_raster(
            Image.fromarray(
                reshape_as_image(arr)
            ).filter(FILTERS[img_filter])
        ),
        1,
        255
    ).astype("uint8")


def blur(arr):
    """
    Apply PIL blur filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "blur")


def contour(arr):
    """
    Apply PIL contour filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "contour")


def detail(arr):
    """
    Apply PIL detail filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "detail")


def edge_enhance(arr):
    """
    Apply PIL edge_enhance filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "edge_enhance")


def edge_enhance_more(arr):
    """
    Apply PIL edge_enhance_more filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "edge_enhance_more")


def emboss(arr):
    """
    Apply PIL emboss filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "emboss")


def find_edges(arr):
    """
    Apply PIL find_edges filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "find_edges")


def sharpen(arr):
    """
    Apply PIL sharpen filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "sharpen")


def smooth(arr):
    """
    Apply PIL smooth filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "smooth")


def smooth_more(arr):
    """
    Apply PIL smooth_more filter to array and return.

    Parameters
    ----------
    arr : 3-dimensional uint8 NumPy array

    Returns
    -------
    NumPy array
    """
    return _apply_filter(arr, "smooth_more")
