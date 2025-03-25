"""CLI command for finding planetary retrograde periods."""

import click
import traceback
from typing import Optional
import os.path

from ..planet import Planet
from ..retrograde.finder import RetrogradeFinder
from .ephemeris import parse_date_input, get_ephemeris_factory, EPHEMERIS_SOURCES, DEFAULT_SOURCE

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
            from ..space_time.julian import julian_to_datetime
            start_date = julian_to_datetime(start_date)
        if isinstance(stop_date, float):
            from ..space_time.julian import julian_to_datetime
            stop_date = julian_to_datetime(stop_date)
            
        # Create appropriate ephemeris instances
        factory = get_ephemeris_factory(source)
        
        # For weft source, handle data paths separately
        if source == "weft":
            if not data:
                # Use default weftball path for the planet
                data = DEFAULT_WEFTBALL_PATHS.get(planet_enum)
                if not data or not os.path.exists(data):
                    raise click.BadParameter(f"Default weftball not found at {data}. Please provide --data parameter.")
            
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
            planet_ephemeris=planet_ephemeris,
            sun_ephemeris=sun_ephemeris
        )
        
        # Find retrograde periods
        periods = finder.find_retrograde_periods(
            planet=planet_enum,
            start_date=start_date,
            end_date=stop_date,
            step=step
        )
        
        # Before outputting, adjust each period so that the pre_shadow_start longitude matches the station_direct longitude.
        # This represents the entry (or ingress) into the retrograde zone.
        serializable_periods = [period.to_dict() for period in periods]
        for period in serializable_periods:
            if period["pre_shadow_start"] is not None:
                period["pre_shadow_start"]["longitude"] = period["station_direct"]["longitude"]
        
        # Output results based on format
        if format == "json":
            import json
            if output:
                with open(output, 'w') as f:
                    json.dump(serializable_periods, f, indent=2)
            else:
                json.dump(serializable_periods, click.get_text_stream('stdout'), indent=2)
                click.echo()
        elif format == "csv":
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
                "station_retrograde_date", "station_retrograde_longitude",
                "sun_aspect_date", "sun_aspect_longitude",
                "station_direct_date", "station_direct_longitude",
                "post_shadow_end_date"
            ]
            
            def write_csv(f):
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for period in serializable_periods:
                    row = {
                        "planet": planet_enum.name,
                        "pre_shadow_start_date": format_date_for_spreadsheet(period.get("pre_shadow_start", {}).get("date", "")),
                        "station_retrograde_date": format_date_for_spreadsheet(period["station_retrograde"]["date"]),
                        "station_retrograde_longitude": period["station_retrograde"]["longitude"],
                        "sun_aspect_date": format_date_for_spreadsheet(period.get("sun_aspect", {}).get("date", "")),
                        "sun_aspect_longitude": period.get("sun_aspect", {}).get("longitude", ""),
                        "station_direct_date": format_date_for_spreadsheet(period["station_direct"]["date"]),
                        "station_direct_longitude": period["station_direct"]["longitude"],
                        "post_shadow_end_date": format_date_for_spreadsheet(period.get("post_shadow_end", {}).get("date", ""))
                    }
                    writer.writerow(row)
            
            if output:
                with open(output, 'w', newline='') as f:
                    write_csv(f)
            else:
                write_csv(click.get_text_stream('stdout'))
        else:  # text format
            if output:
                with open(output, 'w') as f:
                    f.write(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}\n")
                    for i, period in enumerate(serializable_periods, 1):
                        f.write(f"\nPeriod {i}:\n")
                        # TODO: The pre_shadow_start, post_shadow_end, and sun_aspect times need to be computed 
                        # at their exact moments rather than defaulting to midnight
                        events = []
                        if period.get('pre_shadow_start'):
                            events.append((
                                period['pre_shadow_start']['date'],
                                f"  Ingress (pre-shadow start) at: {period['pre_shadow_start']['date']} (longitude: {period['pre_shadow_start']['longitude']:.2f}°)\n"
                            ))
                        events.append((
                            period['station_retrograde']['date'],
                            f"  Stations retrograde at: {period['station_retrograde']['date']} (longitude: {period['station_retrograde']['longitude']:.2f}°)\n"
                        ))
                        if period.get('sun_aspect'):
                            aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                            events.append((
                                period['sun_aspect']['date'],
                                f"  {aspect_type} occurs at: {period['sun_aspect']['date']} (longitude: {period['sun_aspect']['longitude']:.2f}°)\n"
                            ))
                        events.append((
                            period['station_direct']['date'],
                            f"  Stations direct at: {period['station_direct']['date']} (longitude: {period['station_direct']['longitude']:.2f}°)\n"
                        ))
                        if period.get('post_shadow_end'):
                            events.append((
                                period['post_shadow_end']['date'],
                                f"  Egress (post-shadow end) at: {period['post_shadow_end']['date']} (longitude: {period['post_shadow_end']['longitude']:.2f}°)\n"
                            ))
                        
                        # Sort events by date and write them in chronological order
                        events.sort(key=lambda x: x[0])
                        for _, event_text in events:
                            f.write(event_text)
            else:
                click.echo(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}")
                for i, period in enumerate(serializable_periods, 1):
                    click.echo(f"\nPeriod {i}:")
                    # TODO: The pre_shadow_start, post_shadow_end, and sun_aspect times need to be computed 
                    # at their exact moments rather than defaulting to midnight
                    events = []
                    if period.get('pre_shadow_start'):
                        events.append((
                            period['pre_shadow_start']['date'],
                            f"  Ingress (pre-shadow start) at: {period['pre_shadow_start']['date']} (longitude: {period['pre_shadow_start']['longitude']:.2f}°)"
                        ))
                    events.append((
                        period['station_retrograde']['date'],
                        f"  Stations retrograde at: {period['station_retrograde']['date']} (longitude: {period['station_retrograde']['longitude']:.2f}°)"
                    ))
                    if period.get('sun_aspect'):
                        aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                        events.append((
                            period['sun_aspect']['date'],
                            f"  {aspect_type} occurs at: {period['sun_aspect']['date']} (longitude: {period['sun_aspect']['longitude']:.2f}°)"
                        ))
                    events.append((
                        period['station_direct']['date'],
                        f"  Stations direct at: {period['station_direct']['date']} (longitude: {period['station_direct']['longitude']:.2f}°)"
                    ))
                    if period.get('post_shadow_end'):
                        events.append((
                            period['post_shadow_end']['date'],
                            f"  Egress (post-shadow end) at: {period['post_shadow_end']['date']} (longitude: {period['post_shadow_end']['longitude']:.2f}°)"
                        ))
                    
                    # Sort events by date and write them in chronological order
                    events.sort(key=lambda x: x[0])
                    for _, event_text in events:
                        click.echo(event_text)
        
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo("The API request failed. Check your internet connection or try again later.", err=True)
        click.echo("\nStack trace:", err=True)
        click.echo(traceback.format_exc(), err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        click.echo("\nStack trace:", err=True)
        click.echo(traceback.format_exc(), err=True)
        exit(1) 