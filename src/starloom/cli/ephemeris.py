"""CLI commands for interacting with ephemeris data sources."""

import click
from datetime import datetime, timezone
from typing import Optional, Union

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris.quantities import Quantity
from ..horizons.ephemeris import HorizonsEphemeris
from ..horizons.planet import Planet
from ..horizons.location import Location


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


@click.group()
def ephemeris() -> None:
    """Commands for working with ephemeris data sources."""
    pass


@ephemeris.command()
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
def position(
    planet: str,
    date: Optional[str] = None,
    location: Optional[str] = None,
) -> None:
    """Get planetary position data.

    Examples:

    Current time:
       starloom ephemeris position venus

    Specific time:
       starloom ephemeris position venus --date 2025-03-19T20:00:00

    With observer location:
       starloom ephemeris position venus --location 34.0522,-118.2437,0
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
        
        # Print the results
        click.echo(f"Position of {planet} at {time}:")
        for quantity, value in result.items():
            # Format the output based on the quantity type
            if isinstance(value, float):
                click.echo(f"{quantity.name}: {value:.6f}")
            else:
                click.echo(f"{quantity.name}: {value}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo("The API request failed. Check your internet connection or try again later.", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        exit(1) 