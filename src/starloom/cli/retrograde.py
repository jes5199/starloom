"""CLI command for finding planetary retrograde periods."""

import click
import traceback
from typing import Optional, TextIO
import os.path
import sys
import json

from ..planet import Planet
from ..retrograde.finder import RetrogradeFinder
from .ephemeris import (
    parse_date_input,
    get_ephemeris_factory,
    EPHEMERIS_SOURCES,
    DEFAULT_SOURCE,
)
from ..space_time.julian import julian_to_datetime
from ..retrograde.finder import RetrogradePeriod

# Default weftball paths for each planet
DEFAULT_WEFTBALL_PATHS = {
    Planet.MERCURY: "./weftballs/mercury_weftball.tar.gz",
    Planet.VENUS: "./weftballs/venus_weftball.tar.gz",
    Planet.MARS: "./weftballs/mars_weftball.tar.gz",
    Planet.JUPITER: "./weftballs/jupiter_weftball.tar.gz",
    Planet.SATURN: "./weftballs/saturn_weftball.tar.gz",
    Planet.URANUS: "./weftballs/uranus_weftball.tar.gz",
    Planet.NEPTUNE: "./weftballs/neptune_weftball.tar.gz",
    Planet.PLUTO: "./weftballs/pluto_weftball.tar.gz",
    Planet.MOON: "./weftballs/moon_weftball.tar.gz",
}

DEFAULT_SUN_WEFTBALL = "./weftballs/sun_weftball.tar.gz"


def write_period_as_text(period: RetrogradePeriod, output: TextIO) -> None:
    """Write a single retrograde period in text format."""
    events = []
    if period.pre_shadow_start:
        events.append(
            (
                period.pre_shadow_start[0],
                f"  Ingress (pre-shadow start) at: {julian_to_datetime(period.pre_shadow_start[0]).isoformat()} (longitude: {period.pre_shadow_start[1]:.2f}°)\n",
            )
        )
    events.append(
        (
            period.station_retrograde[0],
            f"  Stations retrograde at: {julian_to_datetime(period.station_retrograde[0]).isoformat()} (longitude: {period.station_retrograde[1]:.2f}°)\n",
        )
    )
    if period.sun_aspect:
        aspect_type = (
            "Cazimi"
            if period.planet in [Planet.MERCURY, Planet.VENUS]
            else "Opposition"
        )
        events.append(
            (
                period.sun_aspect[0],
                f"  {aspect_type} occurs at: {julian_to_datetime(period.sun_aspect[0]).isoformat()} (longitude: {period.sun_aspect[1]:.2f}°)\n",
            )
        )
    events.append(
        (
            period.station_direct[0],
            f"  Stations direct at: {julian_to_datetime(period.station_direct[0]).isoformat()} (longitude: {period.station_direct[1]:.2f}°)\n",
        )
    )
    if period.post_shadow_end:
        events.append(
            (
                period.post_shadow_end[0],
                f"  Egress (post-shadow end) at: {julian_to_datetime(period.post_shadow_end[0]).isoformat()} (longitude: {period.post_shadow_end[1]:.2f}°)\n",
            )
        )

    # Sort events by date and write them in chronological order
    events.sort(key=lambda x: x[0])
    for _, event_text in events:
        output.write(event_text)
    output.flush()


def write_period_as_csv(
    period: RetrogradePeriod, output: TextIO, write_header: bool = False
) -> None:
    """Write a single retrograde period in CSV format."""
    import csv
    import dateutil.parser

    def format_date_for_spreadsheet(date_str):
        if not date_str:
            return ""
        # Parse the ISO date string with timezone
        dt = dateutil.parser.parse(date_str)
        # Format as YYYY-MM-DD HH:MM:SS
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    headers = [
        "planet",
        "pre_shadow_start_date",
        "station_retrograde_date",
        "station_retrograde_longitude",
        "sun_aspect_date",
        "sun_aspect_longitude",
        "station_direct_date",
        "station_direct_longitude",
        "post_shadow_end_date",
    ]

    writer = csv.DictWriter(output, fieldnames=headers)
    if write_header:
        writer.writeheader()

    row = {
        "planet": period.planet.name,
        "pre_shadow_start_date": format_date_for_spreadsheet(
            julian_to_datetime(period.pre_shadow_start[0]).isoformat()
            if period.pre_shadow_start
            else ""
        ),
        "station_retrograde_date": format_date_for_spreadsheet(
            julian_to_datetime(period.station_retrograde[0]).isoformat()
        ),
        "station_retrograde_longitude": period.station_retrograde[1],
        "sun_aspect_date": format_date_for_spreadsheet(
            julian_to_datetime(period.sun_aspect[0]).isoformat()
            if period.sun_aspect
            else ""
        ),
        "sun_aspect_longitude": period.sun_aspect[1] if period.sun_aspect else "",
        "station_direct_date": format_date_for_spreadsheet(
            julian_to_datetime(period.station_direct[0]).isoformat()
        ),
        "station_direct_longitude": period.station_direct[1],
        "post_shadow_end_date": format_date_for_spreadsheet(
            julian_to_datetime(period.post_shadow_end[0]).isoformat()
            if period.post_shadow_end
            else ""
        ),
    }
    writer.writerow(row)
    output.flush()


def write_period_as_json(
    period: RetrogradePeriod, output: TextIO, is_first: bool = True
) -> None:
    """Write a single retrograde period in JSON format."""
    if not is_first:
        output.write(",\n")
    json.dump(period.to_dict(), output, indent=2)
    output.flush()


@click.command()
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
    help="Step size for calculations (e.g. '1d', '6h'). Defaults to '1d'.",
)
@click.option(
    "--output",
    help="Output file path. If not specified, outputs to stdout.",
)
@click.option(
    "--format",
    type=click.Choice(["json", "text", "csv"]),
    default="text",
    help="Output format: 'json' for machine-readable data, 'text' for human-readable summary, 'csv' for spreadsheet format. Defaults to 'text'.",
)
@click.option(
    "--source",
    type=click.Choice(EPHEMERIS_SOURCES),
    default=DEFAULT_SOURCE,
    help=f"Ephemeris data source to use. Defaults to {DEFAULT_SOURCE}.",
)
@click.option(
    "--data",
    help="Data source path: directory for local data (sqlite/cached_horizons) or direct path to planet weftball file (weft).",
)
@click.option(
    "--sun-data",
    help="Path to Sun weftball file when using weft source. If not provided, will use --data for Sun positions.",
)
def retrograde(
    planet: str,
    start: str,
    stop: str,
    step: str,
    output: Optional[str],
    format: str,
    source: str = DEFAULT_SOURCE,
    data: Optional[str] = None,
    sun_data: Optional[str] = None,
) -> None:
    """Find retrograde periods for a planet within a date range.

    The output contains:
      - 'pre_shadow_start': when the planet enters the retrograde envelope (often called the ingress).
      - 'station_retrograde': when the planet stops its direct motion and begins retrograde.
      - 'station_direct': when the planet resumes direct motion.
      - 'post_shadow_end': when the planet exits the retrograde envelope.
      - 'sun_aspect': for Mercury/Venus, this is the cazimi moment, which ideally is computed at the exact moment of alignment (not necessarily midnight).

    Examples:

    Find Mercury retrogrades in 2024 using separate weftballs:
        starloom retrograde mercury --start 2024-01-01 --stop 2024-12-31
            --source weft --data mercury.tar.gz --sun-data sun.tar.gz
            --output mercury_2024.json

    Find Mars retrogrades with higher precision:
        starloom retrograde mars --start 2024-01-01 --stop 2025-12-31
            --step 6h --output mars_retro.json

    Using a specific data source:
        starloom retrograde venus --start 2024-01-01 --stop 2024-12-31
            --source sqlite --data ./data --output venus_retro.json
    """
    try:
        # Convert planet name to enum
        try:
            planet_enum = Planet[planet.upper()]
        except KeyError:
            raise click.BadParameter(f"Invalid planet: {planet}")

        # Parse dates
        start_date = parse_date_input(start)
        stop_date = parse_date_input(stop)

        # Convert to datetime if Julian dates were provided
        if isinstance(start_date, float):
            start_date = julian_to_datetime(start_date)
        if isinstance(stop_date, float):
            stop_date = julian_to_datetime(stop_date)

        # Create appropriate ephemeris instances
        factory = get_ephemeris_factory(source)

        # For weft source, handle data paths separately
        if source == "weft":
            if not data:
                # Use default weftball path for the planet
                data = DEFAULT_WEFTBALL_PATHS.get(planet_enum)
                if not data or not os.path.exists(data):
                    raise click.BadParameter(
                        f"Default weftball not found at {data}. Please provide --data parameter."
                    )

            if not sun_data:
                # Use default sun weftball
                if os.path.exists(DEFAULT_SUN_WEFTBALL):
                    sun_data = DEFAULT_SUN_WEFTBALL

            planet_ephemeris = factory(data_dir=data)
            sun_ephemeris = factory(data_dir=sun_data) if sun_data else None
        else:
            planet_ephemeris = factory(data_dir=data)
            sun_ephemeris = None

        # Create retrograde finder
        finder = RetrogradeFinder(
            planet_ephemeris=planet_ephemeris, sun_ephemeris=sun_ephemeris
        )

        # Open output file or use stdout
        output_file = open(output, "w") if output else sys.stdout

        try:
            # Initialize output based on format
            if format == "json":
                output_file.write('{\n  "retrograde_periods": [\n')
            elif format == "text":
                output_file.write(
                    f"Finding retrograde periods for {planet_enum.name}...\n\n"
                )

            # Find and process retrograde periods one at a time
            periods = finder.find_retrograde_periods(
                planet=planet_enum, start_date=start_date, end_date=stop_date, step=step
            )

            # Process each period as it's found
            for i, period in enumerate(periods):
                if format == "json":
                    write_period_as_json(period, output_file, is_first=(i == 0))
                elif format == "csv":
                    write_period_as_csv(period, output_file, write_header=(i == 0))
                else:  # text format
                    if i > 0:
                        output_file.write("\n")
                    output_file.write(f"Period {i + 1}:\n")
                    write_period_as_text(period, output_file)

            # Finalize output based on format
            if format == "json":
                output_file.write("\n  ]\n}")

        finally:
            # Close output file if we opened one
            if output:
                output_file.close()

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo(
            "The API request failed. Check your internet connection or try again later.",
            err=True,
        )
        click.echo("\nStack trace:", err=True)
        click.echo(traceback.format_exc(), err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        click.echo("\nStack trace:", err=True)
        click.echo(traceback.format_exc(), err=True)
        exit(1)
