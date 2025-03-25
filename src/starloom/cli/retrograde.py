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
        
        # For weft source, we need to handle the data paths differently
        if source == "weft":
            if not data:
                raise click.BadParameter("--data is required when using weft source")
            planet_ephemeris = factory(data_dir=data)
            
            # Create separate sun ephemeris if sun-data is provided
            sun_ephemeris = factory(data_dir=sun_data) if sun_data else None
        else:
            # For other sources, use the same data directory for both
            planet_ephemeris = factory(data_dir=data)
            sun_ephemeris = None  # Will use planet_ephemeris for sun positions
        
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
        
        # Output results based on format
        if format == "json":
            # Convert periods to serializable format
            serializable_periods = [
                {
                    "station_retrograde": period.station_retrograde,
                    "station_direct": period.station_direct,
                    "sun_aspect": period.sun_aspect,
                    "planet": period.planet.name
                }
                for period in periods
            ]
            
            # Output JSON
            if output:
                import json
                with open(output, 'w') as f:
                    json.dump(serializable_periods, f, indent=2)
            else:
                json.dump(serializable_periods, click.get_text_stream('stdout'), indent=2)
                click.echo()  # Add newline after JSON
        else:  # text format
            # Print summary
            from ..space_time.julian import julian_to_datetime
            if output:
                with open(output, 'w') as f:
                    f.write(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}\n")
                    for i, period in enumerate(periods, 1):
                        station_r_date = julian_to_datetime(period.station_retrograde[0])
                        station_d_date = julian_to_datetime(period.station_direct[0])
                        f.write(f"\nPeriod {i}:\n")
                        f.write(f"  Stations retrograde at: {station_r_date.isoformat()}\n")
                        f.write(f"  Stations direct at: {station_d_date.isoformat()}\n")
                        
                        if period.sun_aspect:
                            aspect_date = julian_to_datetime(period.sun_aspect[0])
                            aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                            f.write(f"  {aspect_type} occurs at: {aspect_date.isoformat()}\n")
            else:
                click.echo(f"Found {len(periods)} retrograde period(s) for {planet_enum.name}")
                for i, period in enumerate(periods, 1):
                    station_r_date = julian_to_datetime(period.station_retrograde[0])
                    station_d_date = julian_to_datetime(period.station_direct[0])
                    click.echo(f"\nPeriod {i}:")
                    click.echo(f"  Stations retrograde at: {station_r_date.isoformat()}")
                    click.echo(f"  Stations direct at: {station_d_date.isoformat()}")
                    
                    if period.sun_aspect:
                        aspect_date = julian_to_datetime(period.sun_aspect[0])
                        aspect_type = "Cazimi" if planet_enum in [Planet.MERCURY, Planet.VENUS] else "Opposition"
                        click.echo(f"  {aspect_type} occurs at: {aspect_date.isoformat()}")
        
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