from datetime import datetime, timedelta, date, timezone
import pytz

from starloom.constants import SECONDS_PER_LONGITUDE_DEGREE


class NaiveDateTimeError(Exception):
    """Raised when a datetime object has no timezone info."""

    pass


def ensure_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC if it has a timezone.

    Args:
        dt: Datetime to convert

    Returns:
        datetime: UTC datetime

    Raises:
        NaiveDateTimeError: If datetime is naive
    """
    if dt.tzinfo is None:
        raise NaiveDateTimeError("Datetime must have timezone info")
    return dt.astimezone(timezone.utc)


def _get_longitude_offset(longitude: float) -> timedelta:
    """Convert longitude to timezone offset.

    Args:
        longitude: Longitude in degrees

    Returns:
        timedelta: Timezone offset
    """
    return timedelta(seconds=longitude * SECONDS_PER_LONGITUDE_DEGREE)


def get_local_datetime(dt: datetime, longitude: float) -> datetime:
    """Convert UTC datetime to local datetime based on longitude.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees

    Returns:
        datetime: Local datetime
    """
    dt = ensure_utc(dt)
    return dt + _get_longitude_offset(longitude)


def get_local_date(dt: datetime, longitude: float) -> date:
    """Convert UTC datetime to local date based on longitude.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees (positive east)

    Returns:
        Local date
    """
    # For dates, we want to use the date at the given longitude
    # This means we need to adjust the datetime to be at local midnight
    local_dt = get_local_datetime(dt, longitude)
    # If the local time is before noon, use the previous day's date
    if local_dt.hour < 12:
        local_dt = local_dt - timedelta(days=1)
    return local_dt.date()


def get_closest_local_midnight_before(dt: datetime, longitude: float) -> datetime:
    """Find closest local midnight before given datetime.

    Args:
        dt: UTC datetime
        longitude: Longitude in degrees

    Returns:
        datetime: Closest local midnight before given datetime
    """
    local_dt = get_local_datetime(dt, longitude)
    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if local_midnight > local_dt:
        local_midnight -= timedelta(days=1)
    return local_midnight - _get_longitude_offset(longitude)


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to range [-180, 180].

    Args:
        lon: Longitude to normalize

    Returns:
        float: Normalized longitude
    """
    return ((lon + 180) % 360) - 180


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
