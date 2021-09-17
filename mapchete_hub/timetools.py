from datetime import datetime


def date_to_str(date_obj, microseconds=True):
    """Return string from datetime object in the format."""
    return date_obj.strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ" if microseconds else "%Y-%m-%dT%H:%M:%SZ"
    )


def str_to_date(date_str):
    """Convert string to datetime object."""
    if "T" in date_str:
        add_zulu = "Z" if date_str.endswith("Z") else ""
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f" + add_zulu)
        except ValueError:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S" + add_zulu)
    else:
        return datetime(*map(int, date_str.split('-')))
