"""
Timestamp handling.
"""

from mapchete.pretty import pretty_seconds

from datetime import datetime, timedelta, timezone
from typing import Union


def date_to_str(date_obj, microseconds=True):
    """Return string from datetime object in the format."""
    return date_obj.strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ" if microseconds else "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_to_date(date: Union[str, datetime], tzinfo=timezone.utc) -> datetime:
    """Convert string to datetime object."""
    if isinstance(date, datetime):
        out_date = date
    elif "T" in date:
        add_zulu = "Z" if date.endswith("Z") else ""
        try:
            out_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f" + add_zulu)
        except ValueError:
            out_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S" + add_zulu)
    else:
        year, month, day = date.split("-")
        out_date = datetime(year=int(year), month=int(month), day=int(day))
    if out_date.tzinfo is None:
        return out_date.replace(tzinfo=tzinfo)
    return out_date


def interval_to_timedelta(interval: str) -> timedelta:
    time_types = {
        "w": "weeks",
        "d": "days",
        "h": "hours",
        "m": "minutes",
        "s": "seconds",
    }
    for key, value in time_types.items():
        if interval.endswith(key):
            return timedelta(**{value: float(interval[:-1])})
    else:
        raise ValueError(f"cannot not convert {interval} to timedelta")


def passed_time_to_timestamp(passed_time: str) -> datetime:
    return datetime.now(timezone.utc) - interval_to_timedelta(passed_time)


def pretty_time_passed(timestamp: datetime) -> str:
    return pretty_seconds((datetime.now(timezone.utc) - timestamp).total_seconds())
