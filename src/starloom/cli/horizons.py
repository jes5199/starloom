"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime
import pytz
from typing import Optional, List, cast, Union

from ..horizons.planet import Planet
from ..horizons.quantities import Quantities, HorizonsRequestObserverQuantities
from ..horizons.request import HorizonsRequest
from ..horizons.time_spec import TimeSpec
from ..horizons.ephem_type import EphemType


def parse_date_input(date_str: str) -> Union[datetime, float]:
    """Parse a date string into a datetime object or Julian date.

    Args:
        date_str: Date string to parse

    Returns:
        Union[datetime, float]: Parsed datetime object with UTC timezone or Julian date
    """
    # Remove any whitespace and quotes
    date_str = date_str.strip().strip("'")
    
    if date_str.lower() == "now":
        return datetime.now(pytz.UTC)
    try:
        # Try parsing as Julian date first
        return float(date_str)
    except ValueError:
        try:
            # Try parsing with timezone info
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                # If no timezone info, assume UTC
                dt = dt.replace(tzinfo=pytz.UTC)
            return dt
        except ValueError:
            raise click.BadParameter(f"Invalid date format: {date_str}")


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
def ecliptic(
    planet: str,
    date: tuple[str, ...],
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step: Optional[str] = None,
    julian: bool = False,
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
    quantities = Quantities(
        [
            HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value,  # 20
            HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value,  # 31
        ]
    )
    request = HorizonsRequest(
        planet=planet_enum,
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
