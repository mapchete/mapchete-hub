from mapchete_hub import image_filters
import numpy as np
import pytest


def test_blur(array_8bit):
    assert not np.array_equal(image_filters.blur(array_8bit), array_8bit)


def test_contour(array_8bit):
    assert not np.array_equal(image_filters.contour(array_8bit), array_8bit)


def test_detail(array_8bit):
    assert not np.array_equal(image_filters.detail(array_8bit), array_8bit)


def test_edge_enhance(array_8bit):
    assert not np.array_equal(image_filters.edge_enhance(array_8bit), array_8bit)


def test_edge_enhance_more(array_8bit):
    assert not np.array_equal(image_filters.edge_enhance_more(array_8bit), array_8bit)


def test_emboss(array_8bit):
    assert not np.array_equal(image_filters.emboss(array_8bit), array_8bit)


def test_find_edges(array_8bit):
    assert not np.array_equal(image_filters.find_edges(array_8bit), array_8bit)


def test_sharpen(array_8bit):
    assert not np.array_equal(image_filters.sharpen(array_8bit), array_8bit)


def test_smooth(array_8bit):
    assert not np.array_equal(image_filters.smooth(array_8bit), array_8bit)


def test_smooth_more(array_8bit):
    assert not np.array_equal(image_filters.smooth_more(array_8bit), array_8bit)


def test_unsharp_mask(array_8bit):
    assert not np.array_equal(image_filters.unsharp_mask(array_8bit), array_8bit)


def test_median(array_8bit):
    assert not np.array_equal(image_filters.median(array_8bit), array_8bit)


def test_gaussian_blur(array_8bit):
    assert not np.array_equal(image_filters.gaussian_blur(array_8bit), array_8bit)


def test_sharpen_16bit(array_8bit):
    assert not np.array_equal(image_filters.sharpen_16bit(array_8bit), array_8bit)


def test_errors(array_8bit):
    # data type error
    with pytest.raises(TypeError):
        image_filters.blur(array_8bit.astype(np.uint16))

    # dimension error
    with pytest.raises(TypeError):
        image_filters.blur(array_8bit[0])

    # shape error
    with pytest.raises(TypeError):
        image_filters.blur(np.stack([array_8bit[0]]))
