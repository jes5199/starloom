"""Utility functions for ephemeris data formatting."""


def get_zodiac_sign(longitude: float) -> str:
    """Get the zodiac sign for a given ecliptic longitude.

    Args:
        longitude: Ecliptic longitude in degrees (0-360)

    Returns:
        String representing the zodiac sign and degrees
    """
    # Normalize longitude to 0-360 range
    longitude = longitude % 360

    # Define zodiac signs and their starting longitudes
    zodiac_signs = [
        ("Aries", 0),
        ("Taurus", 30),
        ("Gemini", 60),
        ("Cancer", 90),
        ("Leo", 120),
        ("Virgo", 150),
        ("Libra", 180),
        ("Scorpio", 210),
        ("Sagittarius", 240),
        ("Capricorn", 270),
        ("Aquarius", 300),
        ("Pisces", 330),
    ]

    # Find the sign
    for i, (sign, start_deg) in enumerate(zodiac_signs):
        next_start = zodiac_signs[(i + 1) % 12][1]
        if start_deg <= longitude < next_start or (i == 11 and longitude >= start_deg):
            # Calculate degrees within sign
            degrees_in_sign = longitude - start_deg
            return f"{int(degrees_in_sign+0.5)}° {sign} (longitude: {longitude})"

    # Shouldn't reach here
    return f"{longitude}°"


def format_latitude(latitude: float) -> str:
    """Format ecliptic latitude with N/S designation.

    Args:
        latitude: Ecliptic latitude in degrees

    Returns:
        String representing the formatted latitude
    """
    direction = "N" if latitude >= 0 else "S"
    return f"{abs(latitude):.1f}°{direction}"


def format_distance(distance: float) -> str:
    """Format distance in astronomical units (AU).

    Args:
        distance: Distance in astronomical units

    Returns:
        String representing the formatted distance
    """
    return f"{distance:.2f} AU"
