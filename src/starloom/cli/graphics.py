"""CLI commands for generating planetary position visualizations."""

import traceback
import click
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
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

# Default data directory
DEFAULT_DATA = "./weftballs"


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
        return datetime.now(datetime_timezone.utc)

    try:
        # Try parsing as Julian date
        return float(date_str.strip("' "))
    except ValueError:
        # Try parsing as ISO format
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime_timezone.utc)
            return dt
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")


@click.group(name="graphics")
def graphics() -> None:
    """Generate SVG visualizations of planetary positions."""
    pass


@graphics.command(name="positions")
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
    default=DEFAULT_DATA,
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
    "--path/--no-path",
    default=False,
    help="Draw positions as a continuous path instead of dots",
)
def positions(
    planet: str,
    start: str,
    stop: str,
    step: str = "1d",
    source: str = DEFAULT_SOURCE,
    data: str = DEFAULT_DATA,
    output: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    margin: int = 50,
    color: str = "#FF0000",
    path: bool = False,
) -> None:
    """Generate SVG visualization of planetary positions.

    Examples:

    Basic usage with default weft ephemeris:
       starloom graphics positions mars --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00

    Using a specific weftball file:
       starloom graphics positions venus --data venus_weftball.tar.gz --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00

    Custom output and styling:
       starloom graphics positions jupiter --output jupiter_path.svg --width 1000 --height 800 --color "#FFA500" --path

    Using a different ephemeris source:
       starloom graphics positions saturn --source horizons --start 2025-03-19T20:00:00 --stop 2025-03-20T20:00:00
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


@graphics.command(name="retrograde")
@click.argument("planet")
@click.option(
    "--date",
    required=True,
    help="Date to analyze for retrograde motion (ISO format or Julian date)",
)
@click.option(
    "--source",
    type=click.Choice(EPHEMERIS_SOURCES),
    default=DEFAULT_SOURCE,
    help=f"Ephemeris data source to use. Defaults to {DEFAULT_SOURCE}.",
)
@click.option(
    "--data",
    default=DEFAULT_DATA,
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
    default=545,
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
    "--timezone",
    default="UTC",
    help="Timezone for displaying dates and times (e.g. 'America/New_York', 'Europe/London'). Defaults to UTC.",
)
@click.option(
    "--open",
    default=None,
    help="Open the generated file in the specified browser (e.g. 'chrome', 'firefox', 'safari').",
)
def retrograde(
    planet: str,
    date: str,
    source: str = DEFAULT_SOURCE,
    data: str = DEFAULT_DATA,
    output: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    margin: int = 50,
    color: str = "#FF0000",
    timezone: str = "UTC",
    open: Optional[str] = None,
) -> None:
    """Generate SVG visualization of planetary retrograde motion.

    This command generates a visualization showing the planet's motion around the specified date,
    with the retrograde portion highlighted. The visualization includes:
    - The planet's full orbit in a light gray
    - The retrograde motion portion highlighted in the specified color
    - Dots showing the planet's position at each time step
    - Date labels for key points (station retrograde, station direct, opposition)

    Examples:

    Basic usage with default weft ephemeris:
       starloom graphics retrograde mars --date 2025-03-19T20:00:00

    Using a specific weftball file:
       starloom graphics retrograde venus --data venus_weftball.tar.gz --date 2025-03-19T20:00:00

    Custom output and styling:
       starloom graphics retrograde jupiter --output jupiter_retrograde.svg --width 1000 --height 800 --color "#FFA500"

    Using a specific timezone:
       starloom graphics retrograde saturn --date 2025-03-19T20:00:00 --timezone "America/New_York"

    Open in browser after generation:
       starloom graphics retrograde mars --date 2025-03-19T20:00:00 --open chrome
    """
    # Convert planet name to enum
    try:
        planet_enum = Planet[planet.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid planet: {planet}")

    # Parse date and ensure it's timezone-aware
    target_date = parse_date_input(date)
    if isinstance(target_date, datetime):
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=datetime_timezone.utc)

        # Create time specification for a 60-day range centered on the target date
        # Ensure all datetime objects are timezone-aware
        start_date = (target_date - timedelta(days=30)).astimezone(datetime_timezone.utc)
        stop_date = (target_date + timedelta(days=30)).astimezone(datetime_timezone.utc)
        time_spec = TimeSpec.from_range(start_date, stop_date, "1d")
    else:
        # If target_date is a Julian date, convert to datetime for range calculation
        dt = datetime.fromtimestamp((target_date - 2440587.5) * 86400, tz=datetime_timezone.utc)
        start_date = (dt - timedelta(days=30)).astimezone(datetime_timezone.utc)
        stop_date = (dt + timedelta(days=30)).astimezone(datetime_timezone.utc)
        time_spec = TimeSpec.from_range(start_date, stop_date, "1d")

    try:
        # Create appropriate ephemeris instance based on source
        factory = get_ephemeris_factory(source)
        ephemeris_instance = factory(data_dir=data)

        # Get positions for all requested times
        results = ephemeris_instance.get_planet_positions(planet_enum.name, time_spec)

        # Generate output filename if not specified
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"{planet.lower()}_retrograde_{timestamp}.svg"

        # Create painter and draw visualization
        painter = PlanetaryPainter(
            width=width,
            height=height,
            margin=margin,
            planet_color=color,
            display_timezone=timezone,
        )

        # Convert target date to Julian date if it's a datetime
        if isinstance(target_date, datetime):
            target_jd = target_date.timestamp() / 86400 + 2440587.5
        else:
            target_jd = target_date

        painter.draw_retrograde(results, planet_enum, output, target_jd)

        click.echo(f"Generated visualization: {output}")

        # Open the file in the specified browser if requested
        if open:
            import subprocess
            import os
            import platform
            
            # Map browser names to their executable names
            browser_map = {
                'chrome': {
                    'darwin': 'open -a "Google Chrome"',
                    'linux': 'google-chrome',
                    'win32': 'start chrome'
                },
                'firefox': {
                    'darwin': 'open -a Firefox',
                    'linux': 'firefox',
                    'win32': 'start firefox'
                },
                'safari': {
                    'darwin': 'open -a Safari',
                    'linux': 'safari',
                    'win32': 'start safari'
                }
            }
            
            # Get the current operating system
            system = platform.system().lower()
            
            # Get the browser command for the current system
            if open.lower() in browser_map and system in browser_map[open.lower()]:
                browser_cmd = browser_map[open.lower()][system]
                # Convert the file path to an absolute path
                abs_path = os.path.abspath(output)
                # Execute the browser command with the file path
                subprocess.run(f"{browser_cmd} {abs_path}", shell=True)
            else:
                click.echo(f"Warning: Browser '{open}' not supported on {system}", err=True)

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo(
            "The API request failed. Check your internet connection or try again later.",
            err=True,
        )
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        print(traceback.format_exc())
        exit(1)
