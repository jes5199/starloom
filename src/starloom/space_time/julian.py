from datetime import datetime
import juliandate as juliandate_lib
import math
from typing import Tuple, List
from .pythonic_datetimes import ensure_utc
from .rounding import create_and_round_to_millisecond

# Constant for Julian Date precision
JD_PRECISION = 9


def julian_from_datetime(date: datetime) -> float:
    date = ensure_utc(date)
    jd = juliandate_lib.from_gregorian(
        date.year, date.month, date.day, date.hour, date.minute, date.second, 0
    )
    return round(jd, JD_PRECISION)


def julian_from_datetime_with_microseconds(date: datetime) -> float:
    date = ensure_utc(date)
    jd = juliandate_lib.from_gregorian(
        date.year,
        date.month,
        date.day,
        date.hour,
        date.minute,
        date.second,
        date.microsecond,
    )
    return round(jd, JD_PRECISION)


def julian_to_datetime(jd: float) -> datetime:
    (year, month, day, hour, minute, second, microseconds) = (
        juliandate_lib.to_gregorian(jd)
    )
    return create_and_round_to_millisecond(
        microseconds, second, minute, hour, day, month, year
    )


def julian_to_int_frac(jd: float) -> Tuple[int, float]:
    jd_int = math.floor(jd)
    jd_frac = round(jd - jd_int, JD_PRECISION)
    return jd_int, jd_frac


def julian_parts_from_datetime(date: datetime) -> Tuple[int, float]:
    jd = julian_from_datetime(date)
    return julian_to_int_frac(jd)


def julian_parts_from_datetimes(dates: List[datetime]) -> List[Tuple[int, float]]:
    return [julian_parts_from_datetime(date) for date in dates]
