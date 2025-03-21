"""Julian date calculation module.

This module provides functions for converting between datetime objects and Julian dates
using the Meeus algorithm from "Astronomical Algorithms" (2nd ed.).
Only supports dates after 1583 (Gregorian calendar adoption).
"""

from datetime import datetime, timezone
from typing import Union

# Precision for Julian dates (microsecond precision = 12 decimal places)
JD_PRECISION = 12


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    """Convert a Gregorian date to Julian Day Number using Meeus algorithm.

    Args:
        year: Year in Gregorian calendar
        month: Month in Gregorian calendar (1-12)
        day: Day in Gregorian calendar

    Returns:
        Julian Day Number

    Raises:
        ValueError: If date is before 1583 (Gregorian calendar adoption)
    """
    if year < 1583:
        raise ValueError("Dates before 1583 are not supported")

    # Adjust month and year for the algorithm (Jan & Feb are 13 & 14 of prev year)
    if month <= 2:
        year -= 1
        month += 12

    # Calculate A and B terms for the Gregorian calendar
    a = year // 100
    b = 2 - a + (a // 4)

    # Calculate the Julian Day Number using Meeus formula
    jdn = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524
    return jdn


def _day_fraction(hour: int, minute: int, second: int, microsecond: int) -> float:
    """Calculate the fraction of a day from time components.

    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
        microsecond: Microsecond (0-999999)

    Returns:
        Fraction of day (0.0 to 0.99999...)
    """
    # Calculate total seconds in the day with high precision
    total_seconds = hour * 3600 + minute * 60 + second + microsecond / 1_000_000

    # Calculate day fraction (0.0 to 0.99999...)
    return total_seconds / 86400


def jdn_to_julian_date(
    jdn: int, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0
) -> float:
    """Convert a Julian Day Number to a Julian Date.

    Args:
        jdn: Julian Day Number
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
        microsecond: Microsecond (0-999999)

    Returns:
        Julian Date (JD)
    """
    # Calculate the fractional part of the day
    day_fraction = _day_fraction(hour, minute, second, microsecond)

    # Julian Date = JDN - 0.5 (for noon epoch) + day_fraction
    jd = jdn - 0.5 + day_fraction

    # Round to microsecond precision
    return round(jd, JD_PRECISION)


def datetime_to_julian(dt: datetime) -> float:
    """Convert a datetime object to a Julian Date.

    Args:
        dt: datetime object (must be timezone-aware)

    Returns:
        Julian Date (JD)
    """
    # Ensure we have a timezone-aware datetime
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")

    # Convert to UTC
    dt = dt.astimezone(timezone.utc)

    # Extract date and time components
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    microsecond = dt.microsecond

    # Calculate the Julian Day Number for the date
    jdn = gregorian_to_jdn(year, month, day)

    # Add time components to get Julian Date
    jd = jdn_to_julian_date(jdn, hour, minute, second, microsecond)

    # Round to required precision to avoid floating point errors
    return round(jd, JD_PRECISION)


def julian_to_datetime(jd: Union[float, datetime]) -> datetime:
    """Convert a Julian Date to a datetime object using Meeus algorithm.

    Implementation based on the algorithm from Meeus's "Astronomical Algorithms".

    Args:
        jd: Julian Date or datetime object

    Returns:
        datetime object with UTC timezone
    """
    # If input is already a datetime, just return it
    if isinstance(jd, datetime):
        return jd

    # Round Julian date to microsecond precision to avoid floating point errors
    jd = round(jd, JD_PRECISION)

    # Extract the integer and fractional parts
    jd_int = int(jd)
    jd_frac = jd - jd_int

    # Adjust if the fraction is negative
    if jd_frac < 0:
        jd_frac += 1
        jd_int -= 1

    # Add 0.5 to JD (noon epoch adjustment)
    jd_plus_half = jd + 0.5

    # Split into integer and fractional parts
    Z = int(jd_plus_half)
    F = jd_plus_half - Z

    # Calculate A (adjusted Z) for Gregorian calendar correction
    A = Z
    if Z >= 2299161:  # Gregorian calendar cutover point
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - int(alpha / 4)

    # Calculate B, C, D, E according to Meeus algorithm
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)

    # Calculate day with fractional part
    day_with_fraction = B - D - int(30.6001 * E) + F
    day = int(day_with_fraction)

    # Calculate month
    month = E - 1
    if month > 12:
        month -= 12

    # Calculate year
    year = C - 4716
    if month < 3:
        year += 1

    # Extract time components from the fractional part of the day
    fraction_of_day = day_with_fraction - day

    # Convert to hours, minutes, seconds, microseconds
    # Multiply by 24 hours/day
    hours_fraction = fraction_of_day * 24
    hour = int(hours_fraction)

    # Remaining fraction converted to minutes (60 minutes/hour)
    minutes_fraction = (hours_fraction - hour) * 60
    minute = int(minutes_fraction)

    # Remaining fraction converted to seconds (60 seconds/minute)
    seconds_fraction = (minutes_fraction - minute) * 60
    second = int(seconds_fraction)

    # Remaining fraction converted to microseconds (1,000,000 microseconds/second)
    microsecond = round((seconds_fraction - second) * 1_000_000)

    # Handle microsecond rounding (could be 1,000,000 due to rounding)
    if microsecond >= 1_000_000:
        microsecond = 0
        second += 1
        if second >= 60:
            second = 0
            minute += 1
            if minute >= 60:
                minute = 0
                hour += 1
                if hour >= 24:
                    hour = 0
                    day += 1
                    # We won't handle month/year overflow for simplicity

    return datetime(
        year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc
    )
