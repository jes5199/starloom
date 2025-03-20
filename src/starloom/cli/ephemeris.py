"""CLI commands for interacting with ephemeris data sources."""

import click
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Type, cast

from ..horizons.ephemeris import HorizonsEphemeris
from ..horizons.planet import Planet
from ..ephemeris.quantities import Quantity
from ..ephemeris.util import get_zodiac_sign, format_latitude, format_distance
from ..local_horizons.ephemeris import LocalHorizonsEphemeris
from ..cached_horizons.ephemeris import CachedHorizonsEphemeris
from ..ephemeris.time_spec import TimeSpec
from ..space_time.julian import julian_to_datetime


# Define available ephemeris sources
EPHEMERIS_SOURCES: Dict[
    str, Type[Union[HorizonsEphemeris, LocalHorizonsEphemeris, CachedHorizonsEphemeris]]
] = {
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
    multiple=True,
    default=(),
    help="Date(s) to get coordinates for. Can be specified multiple times. Use ISO format or Julian date.",
)
@click.option(
    "--start",
    help="Start date for range (ISO format or Julian date)",
)
@click.option(
    "--stop",
    help="Stop date for range (ISO format or Julian date)",
)
@click.option(
    "--step",
    help="Step size for range (e.g. '1d', '1h', '30m')",
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
    date: tuple[str, ...],
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step: Optional[str] = None,
    source: str = DEFAULT_SOURCE,
    data_dir: str = "./data",
) -> None:
    """Get planetary position data.

    Examples:

    Single time point:
       starloom ephemeris venus --date 2025-03-19T20:00:00

    Multiple time points:
       starloom ephemeris venus --date 2025-03-19T20:00:00 --date 2025-03-19T21:00:00

    Time range:
       starloom ephemeris venus --start 2025-03-19T20:00:00 --stop 2025-03-19T22:00:00 --step 1h

    Using a specific data source:
       starloom ephemeris venus --source sqlite --data-dir ./data
    """
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet: {planet}")

    # Create time specification
    time_spec = None
    if date:
        dates = [parse_date_input(d) for d in date]
        time_spec = TimeSpec.from_dates(dates)
    elif all([start, stop, step]):
        # We know all three are not None here
        start_str = cast(str, start)
        stop_str = cast(str, stop)
        step_str = cast(str, step)

        # Parse dates
        start_date = parse_date_input(start_str)
        stop_date = parse_date_input(stop_str)

        time_spec = TimeSpec.from_range(
            start_date,
            stop_date,
            step_str,
        )
    else:
        # If no time is specified, use current time
        if not date and not (start and stop and step):
            now = datetime.now(timezone.utc)
            time_spec = TimeSpec.from_dates([now])
        else:
            raise click.BadParameter(
                "Must specify either --date or all of --start, --stop, and --step"
            )

    # Create appropriate ephemeris instance based on source
    ephemeris_class = EPHEMERIS_SOURCES.get(source)
    if not ephemeris_class:
        raise click.BadParameter(f"Invalid source: {source}")

    # Create instance based on class type
    if source in ("sqlite", "cached_horizons"):
        ephemeris_instance = ephemeris_class(data_dir=data_dir)  # type: ignore
    else:
        ephemeris_instance = ephemeris_class()

    try:
        # Get positions for all requested times
        results = ephemeris_instance.get_planet_positions(planet_enum.name, time_spec)

        # Print results for each time point
        for jd, position_data in sorted(results.items()):
            # Format the time as Julian date and ISO datetime
            dt = julian_to_datetime(jd)
            date_str = f"JD {jd:.6f} {dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"

            # Get position values
            longitude = position_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)
            if not isinstance(longitude, (int, float)):
                try:
                    longitude = float(longitude) if longitude is not None else 0.0
                except (ValueError, TypeError):
                    longitude = 0.0

            latitude = position_data.get(Quantity.ECLIPTIC_LATITUDE, 0.0)
            if not isinstance(latitude, (int, float)):
                try:
                    latitude = float(latitude) if latitude is not None else 0.0
                except (ValueError, TypeError):
                    latitude = 0.0

            distance = position_data.get(Quantity.DELTA, 0.0)
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
            click.echo(date_str)
            click.echo(
                f"{planet_enum.name.capitalize()} {zodiac_pos}, {lat_formatted}, {distance_formatted}"
            )
            click.echo("")  # Add blank line between entries

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
