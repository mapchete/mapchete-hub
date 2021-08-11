import datetime
import time

from mapchete_hub import timetools


def test_datetime_from_utc():
    ts = datetime.datetime.utcfromtimestamp(time.time())
    ts_str = timetools.date_to_str(ts)
    assert ts_str
    assert timetools.str_to_date(ts_str)