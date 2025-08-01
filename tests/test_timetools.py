import datetime
import time

from mapchete_hub import timetools


def test_datetime_from_utc():
    ts = datetime.datetime.utcfromtimestamp(time.time())
    ts_str = timetools.date_to_str(ts)
    assert ts_str
    assert timetools.parse_to_date(ts_str)


def test_datetime_from_str():
    assert timetools.parse_to_date("2021-08-01")
