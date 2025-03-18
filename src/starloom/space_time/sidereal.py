from datetime import datetime
from starloom.space_time.julian import julian_from_datetime


def sidereal_time_from_julian(julian_date: float, longitude: float) -> float:
    """
    Calculate Local Mean Sidereal Time (LMST) for a given Julian Date and longitude.

    Parameters:
    julian_date (float): The Julian Date in UTC.
    longitude (float): Observer's longitude in degrees.
                       Positive for East of Prime Meridian,
                       Negative for West.

    Returns:
    float: LMST in decimal hours (0 ≤ LMST < 24).
    """
    # Constants
    JD0 = 2451545.0  # Julian Date at J2000.0
    SECONDS_PER_DAY = 86400.0

    # Step 1: Calculate the number of days since J2000.0
    d = julian_date - JD0

    # Step 2: Calculate Julian centuries since J2000.0
    T = d / 36525.0

    # Step 3: Calculate Greenwich Mean Sidereal Time (GMST) in degrees
    # Using the IAU 1982 formula
    GMST = 280.46061837 + 360.98564736629 * d + 0.000387933 * T**2 - (T**3) / 38710000.0

    # Normalize GMST to [0, 360) degrees
    GMST = GMST % 360.0

    # Step 4: Convert GMST from degrees to hours
    GMST_hours = GMST / 15.0  # 360 degrees = 24 hours

    # Step 5: Calculate Local Mean Sidereal Time (LMST)
    LMST_hours = GMST_hours + (longitude / 15.0)

    # Normalize LMST to [0, 24) hours
    LMST_hours = LMST_hours % 24.0

    return LMST_hours


def sidereal_time_from_datetime(dt: datetime, longitude: float) -> float:
    return sidereal_time_from_julian(julian_from_datetime(dt), longitude)
