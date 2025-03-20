"""CLI commands for interacting with ephemeris data sources."""

import click
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Type

from ..horizons.ephemeris import HorizonsEphemeris
from ..horizons.planet import Planet
from ..ephemeris.quantities import Quantity
from ..ephemeris.util import get_zodiac_sign, format_latitude, format_distance
from ..ephemeris.ephemeris import Ephemeris
from ..local_horizons.ephemeris import LocalHorizonsEphemeris
from ..cached_horizons.ephemeris import CachedHorizonsEphemeris


# Define mapping of friendly names to ephemeris classes
EPHEMERIS_SOURCES: Dict[str, Type[Ephemeris]] = {
    "horizons": HorizonsEphemeris,
    "sqlite": LocalHorizonsEphemeris,
    "cached_horizons": CachedHorizonsEphemeris,
}

# Default ephemeris source
DEFAULT_SOURCE = "horizons"


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


@click.command()
@click.argument("planet")
@click.option(
    "--date",
    "-d",
    default=None,
    help="Date to get coordinates for. Use ISO format or Julian date. Defaults to current time.",
)
@click.option(
    "--source",
    type=click.Choice(list(EPHEMERIS_SOURCES.keys())),
    default=DEFAULT_SOURCE,
    help=f"Ephemeris data source to use. Defaults to {DEFAULT_SOURCE}.",
)
@click.option(
    "--data-dir",
    default="./data",
    help="Directory for local data (used with sqlite and cached_horizons sources).",
)
def ephemeris(
    planet: str,
    date: Optional[str] = None,
    source: str = DEFAULT_SOURCE,
    data_dir: str = "./data",
) -> None:
    """Get planetary position data.

    Examples:

    Current time:
       starloom ephemeris venus

    Specific time:
       starloom ephemeris venus --date 2025-03-19T20:00:00

    Using a specific data source:
       starloom ephemeris venus --source sqlite --data-dir ./data
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

    # Create appropriate ephemeris instance based on source
    ephemeris_class = EPHEMERIS_SOURCES.get(source)
    if not ephemeris_class:
        raise click.BadParameter(f"Invalid source: {source}")
    
    if source in ["sqlite", "cached_horizons"]:
        ephemeris_instance = ephemeris_class(data_dir=data_dir)
    else:
        ephemeris_instance = ephemeris_class()

    try:
        result = ephemeris_instance.get_planet_position(planet_enum.name, time)

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
        distance_formatted = format_distance(distance)

        # Print formatted output
        click.echo(f"Source: {source}")
        click.echo(date_str)
        click.echo(
            f"{planet_enum.name.capitalize()} {zodiac_pos}, {lat_formatted}, {distance_formatted}"
        )

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo(
            "The API request failed. Check your internet connection or try again later.",
            err=True,
        )
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        exit(1)
