from datetime import datetime
from typing import cast, Tuple, List

from juliandate import from_gregorian, to_gregorian
from .pythonic_datetimes import ensure_utc
from .rounding import create_and_round_to_millisecond


JD_PRECISION = 6


def julian_from_datetime(dt: datetime) -> float:
    """Convert a datetime object to Julian date.

    Args:
        dt: Datetime object to convert

    Returns:
        float: Julian date
    """
    dt = ensure_utc(dt)
    jd = cast(
        float, from_gregorian(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    )
    return round(jd, JD_PRECISION)


def julian_from_datetime_with_microseconds(date: datetime) -> float:
    """Convert a datetime object to Julian date with microsecond precision.

    Args:
        date: Datetime object to convert

    Returns:
        float: Julian date with microsecond precision
    """
    date = ensure_utc(date)
    jd = cast(
        float,
        from_gregorian(
            date.year,
            date.month,
            date.day,
            date.hour,
            date.minute,
            date.second + date.microsecond / 1_000_000,
        ),
    )
    return round(jd, JD_PRECISION)


def julian_to_datetime(jd: float) -> datetime:
    (year, month, day, hour, minute, second, microseconds) = to_gregorian(jd)
    return create_and_round_to_millisecond(
        microseconds, second, minute, hour, day, month, year
    )


def julian_to_int_frac(jd: float) -> Tuple[int, float]:
    jd_int = int(jd)
    jd_frac = jd - jd_int
    return jd_int, jd_frac


def julian_parts_from_datetime(dt: datetime) -> Tuple[int, float]:
    """Convert a datetime object to Julian date parts.

    Args:
        dt: Datetime object to convert

    Returns:
        Tuple[int, float]: Integer and fractional parts of Julian date
    """
    jd = julian_from_datetime(dt)
    int_part = int(jd)
    frac_part = jd - int_part
    return int_part, frac_part


def julian_parts_from_datetimes(dates: List[datetime]) -> List[Tuple[int, float]]:
    """Convert a list of datetime objects to Julian date parts.

    Args:
        dates: List of datetime objects to convert

    Returns:
        List[Tuple[int, float]]: List of integer and fractional parts of Julian dates
    """
    return [julian_parts_from_datetime(date) for date in dates]


def datetime_from_julian(jd: float) -> datetime:
    """Convert a Julian date to a datetime object.

    Args:
        jd: Julian date to convert

    Returns:
        datetime: Datetime object
    """
    year, month, day, hour, minute, second = cast(
        Tuple[int, int, int, int, int, float], to_gregorian(jd)
    )
    return create_and_round_to_millisecond(
        0, int(second), minute, hour, day, month, year
    )
