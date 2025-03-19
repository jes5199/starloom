"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime
import pytz
from typing import Optional, List, cast

from ..horizons.planet import Planet
from ..horizons.quantities import Quantities
from ..horizons.request import HorizonsRequest
from ..horizons.time_spec import TimeSpec


def parse_date_input(date_str: str) -> datetime:
    """Parse a date string into a datetime object.

    Args:
        date_str: Date string to parse

    Returns:
        datetime: Parsed datetime object
    """
    if date_str.lower() == "now":
        return datetime.now(pytz.UTC)
    return datetime.fromisoformat(date_str)


@click.group()
def horizons() -> None:
    """Commands for interacting with the JPL Horizons API."""
    pass


@horizons.command()
@click.argument("planet")
@click.option(
    "--date",
    "-d",
    multiple=True,
    help="Date(s) to get coordinates for. Can be specified multiple times.",
)
@click.option(
    "--start",
    help="Start date for range (ISO format)",
)
@click.option(
    "--stop",
    help="Stop date for range (ISO format)",
)
@click.option(
    "--step",
    help="Step size for range (e.g. '1d', '1h', '30m')",
)
def ecliptic(
    planet: str,
    date: Optional[List[str]] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step: Optional[str] = None,
) -> None:
    """Get ecliptic coordinates for a planet."""
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
        time_spec = TimeSpec.from_range(
            parse_date_input(start_str),
            parse_date_input(stop_str),
            step_str,
        )
    else:
        raise click.BadParameter(
            "Must specify either --date or all of --start, --stop, and --step"
        )

    # Create and make request
    quantities = Quantities([20, 31])  # Ecliptic lon/lat and distance
    request = HorizonsRequest(
        planet=planet_enum.value,
        quantities=quantities,
        time_spec=time_spec,
    )

    try:
        response = request.make_request()
        click.echo(response)
    except Exception as e:
        raise click.ClickException(str(e))
