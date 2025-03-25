"""CLI command for finding planetary retrograde periods."""

import click
from datetime import datetime, timezone
from typing import Optional

from ..planet import Planet
from ..retrograde.finder import RetrogradeFinder
from .ephemeris import parse_date_input, get_ephemeris_factory, EPHEMERIS_SOURCES, DEFAULT_SOURCE


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
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format: 'json' for machine-readable data, 'text' for human-readable summary. Defaults to 'text'.",
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
                raise click.BadParameter("--data is required when using weft source")
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
        else:  # text format
            if output:
                with open(output, 'w') as f:
                    f.write(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}\n")
                    for i, period in enumerate(serializable_periods, 1):
                        f.write(f"\nPeriod {i}:\n")
                        f.write(f"  Ingress (pre-shadow start) at: {period['pre_shadow_start']['date']} (longitude: {period['pre_shadow_start']['longitude']:.2f}°)\n")
                        f.write(f"  Stations retrograde at: {period['station_retrograde']['date']} (longitude: {period['station_retrograde']['longitude']:.2f}°)\n")
                        f.write(f"  Stations direct at: {period['station_direct']['date']} (longitude: {period['station_direct']['longitude']:.2f}°)\n")
                        f.write(f"  Egress (post-shadow end) at: {period['post_shadow_end']['date']} (longitude: {period['post_shadow_end']['longitude']:.2f}°)\n")
                        if period['sun_aspect']:
                            # Note: For Mercury and Venus, this is typically the cazimi moment.
                            # For higher precision, ensure the calculation does not default to midnight.
                            aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                            f.write(f"  {aspect_type} occurs at: {period['sun_aspect']['date']} (longitude: {period['sun_aspect']['longitude']:.2f}°)\n")
            else:
                click.echo(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}")
                for i, period in enumerate(serializable_periods, 1):
                    click.echo(f"\nPeriod {i}:")
                    click.echo(f"  Ingress (pre-shadow start) at: {period['pre_shadow_start']['date']} (longitude: {period['pre_shadow_start']['longitude']:.2f}°)")
                    click.echo(f"  Stations retrograde at: {period['station_retrograde']['date']} (longitude: {period['station_retrograde']['longitude']:.2f}°)")
                    click.echo(f"  Stations direct at: {period['station_direct']['date']} (longitude: {period['station_direct']['longitude']:.2f}°)")
                    click.echo(f"  Egress (post-shadow end) at: {period['post_shadow_end']['date']} (longitude: {period['post_shadow_end']['longitude']:.2f}°)")
                    if period['sun_aspect']:
                        aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                        click.echo(f"  {aspect_type} occurs at: {period['sun_aspect']['date']} (longitude: {period['sun_aspect']['longitude']:.2f}°)")
        
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo("The API request failed. Check your internet connection or try again later.", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        exit(1) 