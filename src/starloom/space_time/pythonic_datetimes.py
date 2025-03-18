from datetime import datetime, timedelta, date
import pytz

from lib.constants import SECONDS_PER_LONGITUDE_DEGREE


class NaiveDateTimeError(Exception):
    """Exception raised when a naive datetime is provided."""

    pass


def ensure_utc(date: datetime) -> datetime:
    """Ensure the datetime is in UTC, converting if necessary."""
    if date.tzinfo is None:
        raise NaiveDateTimeError("Naive datetime provided. Please specify a timezone.")
    return date.astimezone(pytz.utc)


def _normalize_longitude(longitude: float) -> float:
    """Normalize longitude to [-180, 180] range."""
    return ((longitude + 180) % 360) - 180


def _get_longitude_offset(longitude: float) -> timedelta:
    """Calculate timezone offset from longitude."""
    normalized_longitude = _normalize_longitude(longitude)
    offset_seconds = normalized_longitude * SECONDS_PER_LONGITUDE_DEGREE
    return timedelta(seconds=offset_seconds)


def get_local_datetime(dt: datetime, longitude: float) -> datetime:
    """Convert a UTC datetime to local datetime based on longitude."""
    offset = _get_longitude_offset(longitude)
    return ensure_utc(dt) + offset


def get_closest_local_midnight_before(dt, longitude):
    """
    Calculate the closest local midnight before the given datetime `dt`, based on longitude.
    """
    local_dt = get_local_datetime(dt, longitude)
    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert local midnight back to UTC
    return (local_midnight - _get_longitude_offset(longitude)).replace(microsecond=0)


def get_local_date(dt: datetime, longitude: float) -> date:
    """
    Convert a UTC datetime to local date based on longitude.
    """
    return get_local_datetime(dt, longitude).date()
