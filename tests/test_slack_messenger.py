import traceback

from mapchete.io.raster import read_raster_window
import pytest

from mapchete_hub.observers.slack_messenger import split_long_text


@pytest.mark.parametrize("max_length", [10, 20, 50, 100, 200])
def test_traceback_split(max_length):
    try:
        read_raster_window("some_noneexisting_file", "foo", "bar")
    except Exception as exception:
        text = (
            f"{repr(exception)}\n"
            f"{''.join(traceback.format_tb(exception.__traceback__))}"
        )
    chunks = split_long_text(text, max_length=max_length)
    for chunk in chunks:
        assert len(chunk) <= max_length
        print(chunk)
