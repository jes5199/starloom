"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime, timezone
from typing import List, Optional

from ..horizons.request import HorizonsRequest
from ..horizons.planet import Planet
from ..horizons.time_spec import TimeSpec
from ..ephemeris.quantities import Quantity


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
    type=click.DateTime(),
    help="Specific date(s) to request data for (UTC). Can be specified multiple times.",
)
@click.option(
    "--start", "-s", type=click.DateTime(), help="Start date for date range (UTC)."
)
@click.option(
    "--end", "-e", type=click.DateTime(), help="End date for date range (UTC)."
)
@click.option("--step", type=str, help='Step size for date range (e.g., "1h", "1d").')
def ecliptic(
    planet: str,
    date: List[datetime],
    start: Optional[datetime],
    end: Optional[datetime],
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
        # Convert to UTC if not already
        dates = [
            d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d for d in date
        ]
        time_spec = TimeSpec.from_dates(dates)
    elif all([start, end, step]):
        # Convert to UTC if not already
        start_utc = (
            start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
        )
        end_utc = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
        time_spec = TimeSpec.from_range(start_utc, end_utc, step)
    else:
        raise click.UsageError(
            "Must specify either --date or all of --start, --end, and --step"
        )

    # Create request with ecliptic coordinates and distance
    quantities = [
        Quantity.ECLIPTIC_LONGITUDE,
        Quantity.ECLIPTIC_LATITUDE,
        Quantity.DELTA,
    ]

    req = HorizonsRequest(
        planet=planet_enum,
        quantities=quantities,
        time_spec=time_spec,
    )

    # Make request and print response
    try:
        response = req.make_request()
        click.echo(response)
    except Exception as e:
        raise click.ClickException(str(e))
