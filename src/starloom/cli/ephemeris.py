"""CLI commands for interacting with ephemeris data sources."""

import click
from datetime import datetime, timezone
from typing import Optional, Union

from ..horizons.ephemeris import HorizonsEphemeris
from ..horizons.planet import Planet
from ..horizons.location import Location
from ..ephemeris.quantities import Quantity


def parse_date_input(date_str: str) -> Union[datetime, float]:
    """Parse date input in various formats.

    Args:
        date_str: Date string in various formats:
            - Julian date (e.g., "2460385.333333333")
            - ISO format with timezone (e.g., "2024-03-15T20:00:00+00:00")
            - ISO format without timezone (e.g., "2024-03-15T20:00:00")
            - "now"

    Returns:
        Either a datetime object (for ISO format or "now") or a float (for Julian date)

    Raises:
        ValueError: If date string is invalid
    """
    if date_str.lower() == "now":
        return datetime.now(timezone.utc)

    try:
        # Try parsing as Julian date
        return float(date_str.strip("' "))
    except ValueError:
        # Try parsing as ISO format
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")


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
        ("Pisces", 330)
    ]
    
    # Find the sign
    for i, (sign, start_deg) in enumerate(zodiac_signs):
        next_start = zodiac_signs[(i + 1) % 12][1]
        if start_deg <= longitude < next_start or (i == 11 and longitude >= start_deg):
            # Calculate degrees within sign
            degrees_in_sign = longitude - start_deg
            return f"{sign} {int(degrees_in_sign)}°"
    
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


@click.command()
@click.argument("planet")
@click.option(
    "--date",
    "-d",
    default=None,
    help="Date to get coordinates for. Use ISO format or Julian date. Defaults to current time.",
)
@click.option(
    "--location",
    help="Observer location (lat,lon,elev)",
)
def ephemeris(
    planet: str,
    date: Optional[str] = None,
    location: Optional[str] = None,
) -> None:
    """Get planetary position data.

    Examples:

    Current time:
       starloom ephemeris venus

    Specific time:
       starloom ephemeris venus --date 2025-03-19T20:00:00

    With observer location:
       starloom ephemeris venus --location 34.0522,-118.2437,0
    """
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet: {planet}")

    # Parse date
    if date:
        time = parse_date_input(date)
    else:
        time = datetime.now(timezone.utc)

    # Parse location
    loc = None
    if location:
        try:
            lat, lon, elev = map(float, location.split(","))
            loc = Location(latitude=lat, longitude=lon, elevation=elev)
        except ValueError:
            raise click.BadParameter("Location must be lat,lon,elev")

    # Create ephemeris instance and get position
    ephemeris_instance = HorizonsEphemeris()
    
    try:
        result = ephemeris_instance.get_planet_position(planet_enum.name, time, loc)
        
        # Format the time
        if isinstance(time, datetime):
            date_str = time.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            # It's a Julian date
            date_str = f"JD {time}"
            
        # Get Julian date from result
        julian_date = result.get(Quantity.JULIAN_DATE)
        if julian_date is not None and isinstance(julian_date, (int, float)):
            if isinstance(time, datetime):
                date_str += f", JD {julian_date:.6f}"
            else:
                date_str = f"JD {julian_date:.6f}"
        
        # Get position values
        longitude = result.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
        if not isinstance(longitude, (int, float)):
            try:
                longitude = float(longitude) if longitude is not None else 0.0
            except (ValueError, TypeError):
                longitude = 0.0
                
        latitude = result.get(Quantity.ECLIPTIC_LATITUDE, 0.0)
        if not isinstance(latitude, (int, float)):
            try:
                latitude = float(latitude) if latitude is not None else 0.0
            except (ValueError, TypeError):
                latitude = 0.0
                
        distance = result.get(Quantity.DELTA, 0.0)
        if not isinstance(distance, (int, float)):
            try:
                distance = float(distance) if distance is not None else 0.0
            except (ValueError, TypeError):
                distance = 0.0
        
        # Format position
        zodiac_pos = get_zodiac_sign(longitude)
        lat_formatted = format_latitude(latitude)
        distance_formatted = f"{distance:.2f} AU"
        
        # Print formatted output
        click.echo(date_str)
        click.echo(f"{planet_enum.name.capitalize()} {zodiac_pos}, {lat_formatted}, {distance_formatted}")
        
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo("The API request failed. Check your internet connection or try again later.", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        exit(1)
