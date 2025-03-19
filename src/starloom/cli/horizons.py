"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime, timezone
from typing import List, Optional

from ..horizons.request import HorizonsRequest
from ..horizons.planet import Planet
from ..horizons.time_spec import TimeSpec
from ..ephemeris.quantities import Quantity


def parse_date_input(date_str: str) -> datetime:
    """Parse date input, handling special cases like 'now'."""
    if date_str.lower() == "now":
        return datetime.now(timezone.utc)
    return click.DateTime().convert(date_str, None, None)


@click.group()
def horizons():
    """Commands for interacting with the JPL Horizons API."""
    pass


@horizons.command()
@click.argument("planet", type=str)
@click.option(
    "--date",
    "-d",
    multiple=True,
    type=str,
    help="Specific date(s) to request data for (UTC). Can be specified multiple times. Use 'now' for current time.",
)
@click.option(
    "--start",
    "-s",
    type=str,
    help="Start date for date range (UTC). Use 'now' for current time.",
)
@click.option(
    "--end",
    "-e",
    type=str,
    help="End date for date range (UTC). Use 'now' for current time.",
)
@click.option("--step", type=str, help='Step size for date range (e.g., "1h", "1d").')
def ecliptic(
    planet: str,
    date: List[str],
    start: Optional[str],
    end: Optional[str],
    step: Optional[str],
):
    """Get ecliptic coordinates and distance for a planet."""
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet name: {planet}")

    # Create time specification
    if date:
        # Parse dates, handling 'now' special case
        dates = [parse_date_input(d) for d in date]
        time_spec = TimeSpec.from_dates(dates)
    elif all([start, end, step]):
        # Parse dates, handling 'now' special case
        start_utc = parse_date_input(start)
        end_utc = parse_date_input(end)
        time_spec = TimeSpec.from_range(start_utc, end_utc, step)
    else:
        raise click.UsageError(
            "Must specify either --date or all of --start, --end, and --step"
        )

    # Create request with ecliptic coordinates and distance
    quantities = [
        Quantity.DELTA,  # Distance
        Quantity.DELTA_DOT,  # Range rate
        Quantity.ECLIPTIC_LONGITUDE,  # Ecliptic longitude
        Quantity.ECLIPTIC_LATITUDE,  # Ecliptic latitude
    ]
    request = HorizonsRequest(
        planet=planet_enum,
        quantities=quantities,
        time_spec=time_spec,
    )

    # Make request and print response
    response = request.make_request()
    print(response)
