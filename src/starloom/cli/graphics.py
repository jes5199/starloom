"""CLI commands for generating planetary position visualizations."""

import click
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Protocol, Any, Callable

from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..graphics.painter import PlanetaryPainter


class EphemerisProtocol(Protocol):
    def __init__(self, data_dir: Optional[str] = None) -> None: ...
    def get_planet_positions(
        self, planet: str, time_spec: Any
    ) -> Dict[float, Dict[str, float]]: ...


# Define factory functions for lazy loading ephemeris implementations
def get_ephemeris_factory(source: str) -> Callable[[Optional[str]], EphemerisProtocol]:
    """Get factory function for the requested ephemeris source."""
    if source == "sqlite":

        def factory(data_dir: Optional[str] = None) -> EphemerisProtocol:
            from ..local_horizons.ephemeris import LocalHorizonsEphemeris

            return LocalHorizonsEphemeris(data_dir=data_dir)

        return factory
    elif source == "cached_horizons":

        def factory(data_dir: Optional[str] = None) -> EphemerisProtocol:
            from ..cached_horizons.ephemeris import CachedHorizonsEphemeris

            return CachedHorizonsEphemeris(data_dir=data_dir)

        return factory
    elif source == "weft":

        def factory(data_dir: Optional[str] = None) -> EphemerisProtocol:
            from ..weft_ephemeris.ephemeris import WeftEphemeris

            return WeftEphemeris(data_dir=data_dir)

        return factory
    elif source == "horizons":

        def factory(data_dir: Optional[str] = None) -> EphemerisProtocol:
            from ..horizons.ephemeris import HorizonsEphemeris

            return HorizonsEphemeris()

        return factory
    else:
        raise ValueError(f"Unknown ephemeris source: {source}")


# Available ephemeris sources
EPHEMERIS_SOURCES = ["sqlite", "cached_horizons", "weft", "horizons"]

# Default ephemeris source
DEFAULT_SOURCE = "weft"


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


@click.command(name="graphics")
@click.argument("planet")
@click.option(
    "--start",
    required=True,
    help="Start date for range (ISO format or Julian date)",
)
@click.option(
    "--stop",
    required=True,
    help="Stop date for range (ISO format or Julian date)",
)
@click.option(
    "--step",
    default="1d",
    help="Step size for range (e.g. '1d', '1h', '30m'). Defaults to 1d.",
)
@click.option(
    "--source",
    type=click.Choice(EPHEMERIS_SOURCES),
    default=DEFAULT_SOURCE,
    help=f"Ephemeris data source to use. Defaults to {DEFAULT_SOURCE}.",
)
@click.option(
    "--data",
    default="./data",
    help="Data source path: directory for local data (sqlite/cached_horizons) or direct path to weftball file (weft).",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output SVG file path. If not specified, will use planet name with timestamp.",
)
@click.option(
    "--width",
    default=800,
    help="SVG canvas width in pixels",
)
@click.option(
    "--height",
    default=600,
    help="SVG canvas height in pixels",
)
@click.option(
    "--margin",
    default=50,
    help="Margin around the plot in pixels",
)
@click.option(
    "--color",
    default="#FF0000",
    help="Color for the planet dots/path",
)
@click.option(
    "--background",
    default="#FFFFFF",
    help="Background color of the canvas",
)
@click.option(
    "--path/--no-path",
    default=False,
    help="Draw positions as a continuous path instead of dots",
)
def graphics(
    planet: str,
    start: str,
    stop: str,
    step: str = "1d",
    source: str = DEFAULT_SOURCE,
    data: str = "./data",
    output: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    margin: int = 50,
    color: str = "#FF0000",
    background: str = "#FFFFFF",
    path: bool = False,
) -> None:
    """Generate SVG visualization of planetary positions.

    Examples:

    Basic usage with default weft ephemeris:
       starloom graphics mars --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00

    Using a specific weftball file:
       starloom graphics venus --data venus_weftball.tar.gz --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00

    Custom output and styling:
       starloom graphics jupiter --output jupiter_path.svg --width 1000 --height 800 --color "#FFA500" --path

    Using a different ephemeris source:
       starloom graphics saturn --source horizons --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00
    """
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet: {planet}")

    # Parse dates
    start_date = parse_date_input(start)
    stop_date = parse_date_input(stop)

    # Create time specification
    time_spec = TimeSpec.from_range(start_date, stop_date, step)

    try:
        # Create appropriate ephemeris instance based on source
        factory = get_ephemeris_factory(source)
        ephemeris_instance = factory(data_dir=data)

        # Get positions for all requested times
        results = ephemeris_instance.get_planet_positions(planet_enum.name, time_spec)

        # Generate output filename if not specified
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"{planet.lower()}_{timestamp}.svg"

        # Create painter and draw visualization
        painter = PlanetaryPainter(
            width=width,
            height=height,
            margin=margin,
            planet_color=color,
            background_color=background,
        )

        if path:
            painter.draw_planet_path(results, planet_enum, output)
        else:
            painter.draw_planet_positions(results, planet_enum, output)

        click.echo(f"Generated visualization: {output}")

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
