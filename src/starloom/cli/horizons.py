"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime, timezone
from typing import Optional, cast, Union

from ..horizons.planet import Planet
from ..horizons.quantities import Quantities, HorizonsRequestObserverQuantities
from ..horizons.request import HorizonsRequest
from ..horizons.time_spec import TimeSpec
from ..horizons.ephem_type import EphemType
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
def horizons() -> None:
    """Commands for interacting with the JPL Horizons API."""
    pass


@horizons.command()
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
    "--julian",
    is_flag=True,
    help="Use Julian dates in output",
)
@click.option(
    "--location",
    help="Observer location (lat,lon,elev)",
)
def ecliptic(
    planet: str,
    date: tuple[str, ...],
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step: Optional[str] = None,
    julian: bool = False,
    location: Optional[str] = None,
) -> None:
    """Get ecliptic coordinates for a planet.

    Examples:

    Single time point query:
       starloom horizons ecliptic venus --date 2025-03-19T20:00:00

    Multiple time points or range query:
       starloom horizons ecliptic venus --start 2025-03-19T20:00:00 --stop 2025-03-19T22:00:00 --step 1h
    """
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet: {planet}")

    # Parse location
    loc = None
    if location:
        try:
            lat, lon, elev = map(float, location.split(","))
            loc = Location(latitude=lat, longitude=lon, elevation=elev)
        except ValueError:
            raise click.BadParameter("Location must be lat,lon,elev")

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

    # Create quantities for the request
    quantities = Quantities(
        [
            HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value,  # 20
            HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value,  # 31
        ]
    )

    # Create and make request
    request = HorizonsRequest(
        planet=planet_enum,
        location=loc,
        quantities=quantities,
        time_spec=time_spec,
        use_julian=julian,
    )

    try:
        response = request.make_request()
        click.echo(response)
    except Exception as e:
        import traceback

        click.echo(f"Error: {str(e)}", err=True)
        click.echo("\nTraceback:", err=True)
        click.echo(traceback.format_exc(), err=True)
        raise click.ClickException("Command failed")


@horizons.command()
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
    "--julian",
    is_flag=True,
    help="Use Julian dates in output",
)
def elements(
    planet: str,
    date: tuple[str, ...],
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step: Optional[str] = None,
    julian: bool = False,
) -> None:
    """Get orbital elements for a planet."""
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

        # Parse dates and convert datetime objects to Julian dates if needed
        start_date = parse_date_input(start_str)
        stop_date = parse_date_input(stop_str)

        time_spec = TimeSpec.from_range(
            start_date,
            stop_date,
            step_str,
        )
    else:
        raise click.BadParameter(
            "Must specify either --date or all of --start, --stop, and --step"
        )

    # Create and make request
    quantities = Quantities(
        [
            HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value,  # 20
            HorizonsRequestObserverQuantities.TRUE_ANOMALY_ANGLE.value,  # 41
        ]
    )
    request = HorizonsRequest(
        planet=planet_enum.value,
        quantities=quantities,
        time_spec=time_spec,
        ephem_type=EphemType.ELEMENTS,
        center="10",  # Sun is the center body for orbital elements
        use_julian=julian,
    )

    try:
        response = request.make_request()
        click.echo(response)
    except Exception as e:
        import traceback

        click.echo(f"Error: {str(e)}", err=True)
        click.echo("\nTraceback:", err=True)
        click.echo(traceback.format_exc(), err=True)
        raise click.ClickException("Command failed")
