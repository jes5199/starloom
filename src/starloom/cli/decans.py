"""CLI command for finding decan periods."""

import click
import traceback
from typing import Optional, TextIO
import os.path
import sys
import json
import csv
import dateutil.parser

from ..planet import Planet
from .ephemeris import (
    parse_date_input,
    get_ephemeris_factory,
    EPHEMERIS_SOURCES,
    DEFAULT_SOURCE,
)
from ..space_time.julian import julian_to_datetime

# Default weftball path for Sun
DEFAULT_SUN_WEFTBALL = "./weftballs/sun_weftball.tar.gz"

# Zodiac signs and their starting longitudes
ZODIAC_SIGNS = [
    ("Aries", 0),
    ("Taurus", 30),
    ("Gemini", 60),
    ("Cancer", 90),
    ("Leo", 120),
    ("Virgo", 150),
    ("Libra", 180),
    ("Scorpio", 210),
    ("Sagittarius", 240),
    ("Capricorn", 270),
    ("Aquarius", 300),
    ("Pisces", 330),
]

def get_zodiac_sign(longitude: float) -> tuple[str, int]:
    """Get the zodiac sign and decan number for a given ecliptic longitude.
    
    Args:
        longitude: Ecliptic longitude in degrees (0-360)
        
    Returns:
        Tuple of (sign name, decan number 1-3)
    """
    # Normalize longitude to 0-360 range
    longitude = longitude % 360
    
    # Find the sign
    for i, (sign, start_deg) in enumerate(ZODIAC_SIGNS):
        next_start = ZODIAC_SIGNS[(i + 1) % 12][1]
        if start_deg <= longitude < next_start or (i == 11 and longitude >= start_deg):
            # Calculate decan number (1-3)
            degrees_in_sign = longitude - start_deg
            decan = int(degrees_in_sign / 10) + 1
            return sign, decan
            
    # Shouldn't reach here
    return "Unknown", 0

def write_decan_as_text(decan_data: dict, output: TextIO) -> None:
    """Write a single decan period in text format."""
    output.write(f"Decan {decan_data['decan']} of {decan_data['sign']}:\n")
    output.write(f"  Ingress at: {decan_data['ingress_date']} (longitude: {decan_data['ingress_longitude']:.2f}°)\n")
    output.write(f"  Egress at: {decan_data['egress_date']} (longitude: {decan_data['egress_longitude']:.2f}°)\n")
    output.flush()

def write_decan_as_csv(decan_data: dict, output: TextIO, write_header: bool = False) -> None:
    """Write a single decan period in CSV format."""
    headers = [
        "sign",
        "decan",
        "ingress_date",
        "ingress_longitude",
        "egress_date",
        "egress_longitude"
    ]
    
    writer = csv.DictWriter(output, fieldnames=headers)
    if write_header:
        writer.writeheader()
        
    writer.writerow(decan_data)
    output.flush()

def write_decan_as_json(decan_data: dict, output: TextIO, is_first: bool = True) -> None:
    """Write a single decan period in JSON format."""
    if not is_first:
        output.write(",\n")
    json.dump(decan_data, output, indent=2)
    output.flush()

@click.command()
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
    default="1h",
    help="Step size for calculations (e.g. '1h', '15m'). Defaults to '1h'.",
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
    help="Data source path: directory for local data (sqlite/cached_horizons) or direct path to sun weftball file (weft).",
)
def decans(
    start: str,
    stop: str,
    step: str,
    output: Optional[str],
    format: str,
    source: str = DEFAULT_SOURCE,
    data: Optional[str] = None,
) -> None:
    """Find decan periods for the Sun within a date range.
    
    The output contains:
      - 'ingress_date': when the Sun enters a decan
      - 'ingress_longitude': the Sun's ecliptic longitude at ingress
      - 'egress_date': when the Sun exits a decan
      - 'egress_longitude': the Sun's ecliptic longitude at egress
      - 'sign': the zodiac sign containing the decan
      - 'decan': the decan number (1-3) within the sign
      
    Examples:
    
    Find decans in 2024 using default weftball:
        starloom decans --start 2024-01-01 --stop 2024-12-31
            --source weft --data sun.tar.gz
            --output decans_2024.json
            
    Find decans with higher precision:
        starloom decans --start 2024-01-01 --stop 2024-12-31
            --step 15m --output decans_2024.json
            
    Using a specific data source:
        starloom decans --start 2024-01-01 --stop 2024-12-31
            --source sqlite --data ./data --output decans_2024.json
    """
    try:
        # Parse dates
        start_date = parse_date_input(start)
        stop_date = parse_date_input(stop)
        
        # Convert to datetime if Julian dates were provided
        if isinstance(start_date, float):
            start_date = julian_to_datetime(start_date)
        if isinstance(stop_date, float):
            stop_date = julian_to_datetime(stop_date)
            
        # Create appropriate ephemeris instance
        factory = get_ephemeris_factory(source)
        
        # For weft source, handle data path
        if source == "weft":
            if not data:
                # Use default sun weftball path
                data = DEFAULT_SUN_WEFTBALL
                if not os.path.exists(data):
                    raise click.BadParameter(
                        f"Default sun weftball not found at {data}. Please provide --data parameter."
                    )
                    
            sun_ephemeris = factory(data_dir=data)
        else:
            sun_ephemeris = factory(data_dir=data)
            
        # Open output file or use stdout
        output_file = open(output, "w") if output else sys.stdout
        
        try:
            # Initialize output based on format
            if format == "json":
                output_file.write('{\n  "decan_periods": [\n')
            elif format == "text":
                output_file.write("Finding decan periods for the Sun...\n\n")
                
            # Get Sun positions at regular intervals
            current_date = start_date
            current_longitude = None
            current_sign = None
            current_decan = None
            
            while current_date <= stop_date:
                # Get Sun's ecliptic longitude
                jd = current_date.timestamp() / 86400 + 2440587.5
                pos_data = sun_ephemeris.get_position(jd)
                longitude = pos_data.get("ECLIPTIC_LONGITUDE", 0.0)
                
                # Get current sign and decan
                sign, decan = get_zodiac_sign(longitude)
                
                # Check for decan changes
                if current_longitude is not None:
                    current_sign_deg = next(deg for s, deg in ZODIAC_SIGNS if s == current_sign)
                    current_decan_start = current_sign_deg + (current_decan - 1) * 10
                    current_decan_end = current_decan_start + 10
                    
                    # Check if we've crossed a decan boundary
                    if (current_longitude < current_decan_start and longitude >= current_decan_start) or \
                       (current_longitude < current_decan_end and longitude >= current_decan_end):
                        # Write the previous decan period
                        decan_data = {
                            "sign": current_sign,
                            "decan": current_decan,
                            "ingress_date": current_date.isoformat(),
                            "ingress_longitude": longitude,
                            "egress_date": current_date.isoformat(),
                            "egress_longitude": longitude
                        }
                        
                        if format == "json":
                            write_decan_as_json(decan_data, output_file, is_first=(current_date == start_date))
                        elif format == "csv":
                            write_decan_as_csv(decan_data, output_file, write_header=(current_date == start_date))
                        else:  # text format
                            if current_date != start_date:
                                output_file.write("\n")
                            write_decan_as_text(decan_data, output_file)
                
                current_longitude = longitude
                current_sign = sign
                current_decan = decan
                
                # Move to next time step
                current_date = current_date + dateutil.parser.parse(step)
                
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