from datetime import datetime, timezone
from typing import Tuple, List

from .pythonic_datetimes import ensure_utc
from .rounding import create_and_round_to_millisecond
from .julian_calc import (
    datetime_to_julian,
    julian_to_datetime as _julian_to_datetime
)

JD_PRECISION = 9


def julian_from_datetime(dt: datetime) -> float:
    """Convert datetime to Julian date.

    Args: 
        dt: Datetime to convert

    Returns:
        float: Julian date
    """
    dt = ensure_utc(dt)
    return datetime_to_julian(dt)


def julian_from_datetime_with_microseconds(dt: datetime) -> float:
    """Convert datetime to Julian date with microsecond precision.

    Args:
        dt: Datetime to convert

    Returns:
        float: Julian date with microsecond precision
    """
    dt = ensure_utc(dt)
    return datetime_to_julian(dt)


def julian_to_datetime(jd: float) -> datetime:
    """Convert Julian date to datetime.

    Args:
        jd: Julian date to convert

    Returns:
        datetime: Datetime
    """
    dt = _julian_to_datetime(jd)
    return create_and_round_to_millisecond(
        dt.microsecond, dt.second, dt.minute, dt.hour,
        dt.day, dt.month, dt.year
    )


def julian_to_int_frac(jd: float) -> Tuple[int, float]:
    """Split Julian date into integer and fractional parts.

    Args:
        jd: Julian date to split

    Returns:
        Tuple[int, float]: Integer and fractional parts
    """
    jd_int = int(jd)
    jd_frac = round(jd - jd_int, JD_PRECISION)
    return jd_int, jd_frac


def julian_parts_from_datetime(dt: datetime) -> Tuple[int, float]:
    """Get integer and fractional parts of Julian date.

    Args:
        dt: Datetime to convert

    Returns:
        Tuple[int, float]: Integer and fractional parts
    """
    jd = julian_from_datetime(dt)
    return julian_to_int_frac(jd)


def julian_parts_from_datetimes(dates: List[datetime]) -> List[Tuple[int, float]]:
    """Get integer and fractional parts of Julian dates.

    Args:
        dates: List of datetimes to convert

    Returns:
        List[Tuple[int, float]]: List of integer and fractional parts
    """
    return [julian_parts_from_datetime(date) for date in dates]


def datetime_from_julian(jd: float) -> datetime:
    """Convert Julian date to datetime.

    Args:
        jd: Julian date to convert

    Returns:
        datetime: Datetime
    """
    year, month, day, hour, minute, second = juliandate.to_gregorian(jd)
    return datetime(year, month, day, hour, minute, int(second), tzinfo=timezone.utc)
