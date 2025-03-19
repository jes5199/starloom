from datetime import datetime, timedelta, date
import pytz

from starloom.constants import SECONDS_PER_LONGITUDE_DEGREE


class NaiveDateTimeError(Exception):
    """Exception raised when a naive datetime is provided."""

    pass


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is in UTC.

    Args:
        dt: Datetime to convert

    Returns:
        datetime: UTC datetime
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(pytz.UTC)


def get_local_datetime(dt: datetime, longitude: float) -> datetime:
    """Get local datetime for a given longitude.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees

    Returns:
        datetime: Local datetime
    """
    dt = ensure_utc(dt)
    offset = timedelta(seconds=longitude * SECONDS_PER_LONGITUDE_DEGREE)
    return dt + offset


def get_local_date(dt: datetime, longitude: float) -> date:
    """Get local date for a given longitude.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees

    Returns:
        date: Local date
    """
    return get_local_datetime(dt, longitude).date()


def _get_longitude_offset(longitude: float) -> timedelta:
    """Calculate time offset for a given longitude.

    Args:
        longitude: Longitude in degrees

    Returns:
        timedelta: Time offset
    """
    return timedelta(seconds=longitude * SECONDS_PER_LONGITUDE_DEGREE)


def _normalize_longitude(longitude: float) -> float:
    """Normalize longitude to -180 to 180 range.

    Args:
        longitude: Longitude in degrees

    Returns:
        float: Normalized longitude
    """
    while longitude > 180:
        longitude -= 360
    while longitude < -180:
        longitude += 360
    return longitude


def get_closest_local_midnight_before(dt: datetime, longitude: float) -> datetime:
    """Calculate the closest local midnight before the given datetime.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees

    Returns:
        datetime: UTC datetime of closest local midnight before dt
    """
    local_dt = get_local_datetime(dt, longitude)
    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert local midnight back to UTC
    return (local_midnight - _get_longitude_offset(longitude)).replace(microsecond=0)


def get_utc_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    """Create a UTC datetime object.

    Args:
        year: Year
        month: Month (1-12)
        day: Day of month
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
        microsecond: Microsecond (0-999999)

    Returns:
        datetime: UTC datetime object
    """
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        tzinfo=pytz.UTC,
    )
