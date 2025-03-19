from datetime import datetime, timezone
from typing import Tuple, List
import juliandate

from .pythonic_datetimes import ensure_utc
from .rounding import create_and_round_to_millisecond


JD_PRECISION = 9


def julian_from_datetime(dt: datetime) -> float:
    """Convert datetime to Julian date.

    Args:
        dt: Datetime to convert

    Returns:
        float: Julian date
    """
    dt = ensure_utc(dt)
    return round(
        juliandate.from_gregorian(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        ),
        JD_PRECISION,
    )


def julian_from_datetime_with_microseconds(dt: datetime) -> float:
    """Convert datetime to Julian date with microsecond precision.

    Args:
        dt: Datetime to convert

    Returns:
        float: Julian date with microsecond precision
    """
    dt = ensure_utc(dt)
    return round(
        juliandate.from_gregorian(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second + dt.microsecond / 1_000_000,
        ),
        JD_PRECISION,
    )


def julian_to_datetime(jd: float) -> datetime:
    (year, month, day, hour, minute, second, microseconds) = juliandate.to_gregorian(jd)
    return create_and_round_to_millisecond(
        microseconds, second, minute, hour, day, month, year
    )


def julian_to_int_frac(jd: float) -> Tuple[int, float]:
    jd_int = int(jd)
    jd_frac = jd - jd_int
    return jd_int, jd_frac


def julian_parts_from_datetime(dt: datetime) -> Tuple[int, float]:
    """Get integer and fractional parts of Julian date.

    Args:
        dt: Datetime to convert

    Returns:
        Tuple[int, float]: Integer and fractional parts
    """
    jd = julian_from_datetime(dt)
    jd_int = int(jd)
    jd_frac = round(jd - jd_int, JD_PRECISION)
    return jd_int, jd_frac


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
