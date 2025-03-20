"""CLI commands for interacting with the Horizons API."""

import click
from datetime import datetime, timezone
from typing import Optional, List, cast, Union

from ..horizons.planet import Planet
from ..horizons.quantities import Quantities, HorizonsRequestObserverQuantities
from ..horizons.request import HorizonsRequest
from ..horizons.time_spec import TimeSpec
from ..horizons.ephem_type import EphemType
from ..horizons.observer_parser import ObserverParser
from ..horizons.location import Location


def parse_date_input(date_str: str) -> float:
    """Parse date input in various formats.

    Args:
        date_str: Date string in various formats:
            - Julian date (e.g., "2460385.333333333")
            - ISO format with timezone (e.g., "2024-03-15T20:00:00+00:00")
            - ISO format without timezone (e.g., "2024-03-15T20:00:00")
            - "now"

    Returns:
        Julian date as float

    Raises:
        ValueError: If date string is invalid
    """
    if date_str.lower() == "now":
        return datetime.now(timezone.utc).timestamp() / 86400 + 2440587.5

    try:
        # Try parsing as Julian date
        return float(date_str.strip("' "))
    except ValueError:
        # Try parsing as ISO format
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp() / 86400 + 2440587.5
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")


@click.group()
def horizons() -> None:
    """Commands for interacting with the JPL Horizons API."""
    pass


@horizons.command()
@click.argument("planet", type=click.Choice([p.name.lower() for p in Planet]))
@click.option("--date", help="Date in various formats (Julian, ISO, or 'now')")
@click.option("--julian", is_flag=True, help="Use Julian date format")
@click.option("--location", help="Observer location (lat,lon,elev)")
def ecliptic(planet: str, date: str, julian: bool, location: str):
    """Get ecliptic coordinates for a planet."""
    # Parse planet
    planet = Planet[planet.upper()]

    # Parse date
    if date:
        jd = parse_date_input(date)
    else:
        jd = datetime.now(timezone.utc).timestamp() / 86400 + 2440587.5

    # Parse location
    loc = None
    if location:
        try:
            lat, lon, elev = map(float, location.split(","))
            loc = Location(latitude=lat, longitude=lon, elevation=elev)
        except ValueError:
            raise click.BadParameter("Location must be lat,lon,elev")

    # Create request
    req = HorizonsRequest(planet, location=loc)
    req.time_spec = TimeSpec.from_dates([datetime.fromtimestamp((jd - 2440587.5) * 86400, timezone.utc)])
    req.use_julian = julian

    # Make request
    response = req.make_request()

    # Parse response
    parser = ObserverParser(response)
    data = parser.parse()

    # Print results
    for jd, values in data:
        if julian:
            click.echo(f"JD: {jd}")
        else:
            dt = datetime.fromtimestamp((jd - 2440587.5) * 86400, timezone.utc)
            click.echo(f"Date: {dt.isoformat()}")
        click.echo(f"Distance: {values[EphemerisQuantity.DISTANCE]} AU")
        click.echo(f"Range rate: {values[EphemerisQuantity.RANGE_RATE]} km/s")
        click.echo(f"Ecliptic longitude: {values[EphemerisQuantity.ECLIPTIC_LONGITUDE]}°")
        click.echo(f"Ecliptic latitude: {values[EphemerisQuantity.ECLIPTIC_LATITUDE]}°")
        click.echo()


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
