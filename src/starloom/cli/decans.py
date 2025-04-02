"""CLI command for finding decan periods."""

import click
import traceback
from typing import Optional, TextIO, Tuple
import os.path
import sys
import json
import csv
import dateutil.parser
from datetime import datetime, timedelta

from ..planet import Planet
from .ephemeris import (
    parse_date_input,
    get_ephemeris_factory,
    EPHEMERIS_SOURCES,
    DEFAULT_SOURCE,
)
from ..space_time.julian import julian_to_datetime, datetime_to_julian
from ..ephemeris import Quantity

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

def parse_step_size(step: str) -> timedelta:
    """Parse a step size string into a timedelta.
    
    Args:
        step: Step size string (e.g. '1d', '6h', '15m')
        
    Returns:
        timedelta object
    """
    # Remove any whitespace
    step = step.strip()
    
    # Get the unit and value
    unit = step[-1].lower()
    value = int(step[:-1])
    
    # Convert to timedelta
    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    else:
        raise ValueError(f"Invalid step size unit: {unit}. Use 'd' for days, 'h' for hours, or 'm' for minutes.")

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

def get_sun_longitude(ephemeris, date: datetime) -> float:
    """Get the Sun's ecliptic longitude at a given date."""
    pos_data = ephemeris.get_planet_position("sun", date)
    return pos_data.get(Quantity.ECLIPTIC_LONGITUDE, 0.0)

def find_transition(
    ephemeris,
    start_date: datetime,
    end_date: datetime,
    target_longitude: float,
    tolerance: float = 0.0001,  # About 0.36 seconds of arc
    max_iterations: int = 50
) -> Tuple[datetime, float]:
    """Find the exact time when the Sun's longitude crosses a target value.
    
    Uses binary search to find the transition time with high precision.
    
    Args:
        ephemeris: The ephemeris instance to use
        start_date: Start of search range
        end_date: End of search range
        target_longitude: The target longitude to find
        tolerance: The precision to achieve (in degrees)
        max_iterations: Maximum number of binary search iterations
        
    Returns:
        Tuple of (transition datetime, exact longitude at transition)
    """
    start_longitude = get_sun_longitude(ephemeris, start_date)
    end_longitude = get_sun_longitude(ephemeris, end_date)
    
    # Normalize longitudes to be close to target
    start_longitude = ((start_longitude - target_longitude + 180) % 360) - 180 + target_longitude
    end_longitude = ((end_longitude - target_longitude + 180) % 360) - 180 + target_longitude
    
    # Check if we have a transition in this range
    if (start_longitude - target_longitude) * (end_longitude - target_longitude) > 0:
        raise ValueError("No transition found in given range")
    
    # Binary search
    left_date = start_date
    right_date = end_date
    iterations = 0
    
    while iterations < max_iterations:
        mid_date = left_date + (right_date - left_date) / 2
        mid_longitude = get_sun_longitude(ephemeris, mid_date)
        
        # Normalize mid longitude to be close to target
        mid_longitude = ((mid_longitude - target_longitude + 180) % 360) - 180 + target_longitude
        
        # Check if we've reached desired precision
        if abs(mid_longitude - target_longitude) < tolerance:
            return mid_date, mid_longitude
            
        # Update search range
        if (mid_longitude - target_longitude) * (start_longitude - target_longitude) > 0:
            left_date = mid_date
        else:
            right_date = mid_date
            
        iterations += 1
        
    # Return best estimate if we hit max iterations
    return mid_date, mid_longitude

def format_longitude(lon: float, precision: int = 3) -> str:
    """Format a longitude value, converting 360 to 0 and rounding to specified precision.
    
    Args:
        lon: The longitude value to format
        precision: Number of decimal places to show
        
    Returns:
        Formatted longitude string
    """
    if lon is None:
        return ""
    normalized = round(lon % 360, precision)  # Round before checking for 360
    return f"{0.000 if abs(normalized - 360) < 0.001 else normalized:.{precision}f}"

def write_decan_as_text(decan_data: dict, output: TextIO) -> None:
    """Write a single decan period in text format."""
    output.write(f"Decan {decan_data['decan']} of {decan_data['sign']}:\n")
    
    if decan_data['ingress_date'] is not None:
        output.write(f"  Ingress at: {decan_data['ingress_date']} (longitude: {format_longitude(decan_data['ingress_longitude'], 6)}°)\n")
    
    if decan_data['egress_date'] is not None:
        output.write(f"  Egress at: {decan_data['egress_date']} (longitude: {format_longitude(decan_data['egress_longitude'], 6)}°)\n")
    
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
    
    # Convert None to empty string for CSV and normalize/round longitudes
    row = {
        "sign": decan_data["sign"],
        "decan": decan_data["decan"],
        "ingress_date": decan_data["ingress_date"] if decan_data["ingress_date"] is not None else "",
        "ingress_longitude": format_longitude(decan_data["ingress_longitude"]),
        "egress_date": decan_data["egress_date"] if decan_data["egress_date"] is not None else "",
        "egress_longitude": format_longitude(decan_data["egress_longitude"])
    }
    writer.writerow(row)
    output.flush()

def write_decan_as_json(decan_data: dict, output: TextIO, is_first: bool = True) -> None:
    """Write a single decan period in JSON format."""
    if not is_first:
        output.write(",\n")
    json.dump(decan_data, output, indent=2)
    output.flush()

def get_decan_boundaries(sign: str, decan: int) -> tuple[float, float]:
    """Get the start and end longitudes for a decan.
    
    Args:
        sign: The zodiac sign name
        decan: The decan number (1-3)
        
    Returns:
        Tuple of (start_longitude, end_longitude)
    """
    sign_deg = next(deg for s, deg in ZODIAC_SIGNS if s == sign)
    decan_start = sign_deg + (decan - 1) * 10
    decan_end = decan_start + 10
    return decan_start, decan_end

def get_next_decan(sign: str, decan: int) -> tuple[str, int]:
    """Get the next decan after the given one.
    
    Args:
        sign: The current zodiac sign name
        decan: The current decan number (1-3)
        
    Returns:
        Tuple of (next_sign, next_decan)
    """
    if decan < 3:
        # Next decan is in the same sign
        return sign, decan + 1
    else:
        # Next decan is in the next sign
        current_idx = next(i for i, (s, _) in enumerate(ZODIAC_SIGNS) if s == sign)
        next_idx = (current_idx + 1) % 12
        next_sign = ZODIAC_SIGNS[next_idx][0]
        return next_sign, 1

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
    default="1d",
    help="Step size for initial search (e.g. '1d', '6h', '15m'). Defaults to '1d'.",
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
            --step 6h --output decans_2024.json
            
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
                
            # Get Sun positions at regular intervals to find potential transitions
            current_date = start_date
            step_delta = parse_step_size(step)
            
            # Track the current decan we're in
            current_sign = None
            current_decan = None
            current_ingress_date = None
            current_ingress_longitude = None
            
            # Track output state
            is_first = True
            
            while current_date <= stop_date:
                # Get Sun's ecliptic longitude
                longitude = get_sun_longitude(sun_ephemeris, current_date)
                sign, decan = get_zodiac_sign(longitude)
                
                # Check if we've changed decans
                if sign != current_sign or decan != current_decan:
                    if current_sign is not None:
                        # We've found a transition - get the exact time
                        decan_start, decan_end = get_decan_boundaries(current_sign, current_decan)
                        try:
                            # Find exact transition time
                            transition_date, transition_longitude = find_transition(
                                sun_ephemeris,
                                current_date - step_delta,  # Search window
                                current_date,
                                decan_end
                            )
                            
                            # Write the completed decan period
                            decan_data = {
                                "sign": current_sign,
                                "decan": current_decan,
                                "ingress_date": current_ingress_date,
                                "ingress_longitude": current_ingress_longitude,
                                "egress_date": transition_date.isoformat(),
                                "egress_longitude": transition_longitude
                            }
                            
                            if format == "json":
                                write_decan_as_json(decan_data, output_file, is_first=is_first)
                                is_first = False
                            elif format == "csv":
                                write_decan_as_csv(decan_data, output_file, write_header=is_first)
                                is_first = False
                            else:  # text format
                                if not is_first:
                                    output_file.write("\n")
                                write_decan_as_text(decan_data, output_file)
                                is_first = False
                            
                        except ValueError:
                            # No transition found in this range, use current time as approximation
                            pass
                    
                    # Start tracking the new decan
                    current_sign = sign
                    current_decan = decan
                    
                    # Find exact ingress time using binary search
                    try:
                        decan_start, _ = get_decan_boundaries(sign, decan)
                        ingress_date, ingress_longitude = find_transition(
                            sun_ephemeris,
                            current_date - step_delta,  # Search window
                            current_date,
                            decan_start
                        )
                        current_ingress_date = ingress_date.isoformat()
                        current_ingress_longitude = ingress_longitude
                    except ValueError:
                        # If we can't find exact ingress, use current time as fallback
                        current_ingress_date = current_date.isoformat()
                        current_ingress_longitude = longitude
                
                # Move to next time step
                current_date += step_delta
                
            # Write the final decan if we have one
            if current_sign is not None:
                decan_data = {
                    "sign": current_sign,
                    "decan": current_decan,
                    "ingress_date": current_ingress_date,
                    "ingress_longitude": current_ingress_longitude,
                    "egress_date": None,  # Still in this decan
                    "egress_longitude": None
                }
                
                if format == "json":
                    write_decan_as_json(decan_data, output_file, is_first=is_first)
                elif format == "csv":
                    write_decan_as_csv(decan_data, output_file, write_header=is_first)
                else:  # text format
                    if not is_first:
                        output_file.write("\n")
                    write_decan_as_text(decan_data, output_file)
                
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