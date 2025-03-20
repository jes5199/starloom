"""
CLI commands for generating and using .weft files.
"""

import click
import os

from ..weft import generate_weft_file
from ..horizons.quantities import EphemerisQuantity
from .horizons import parse_date_input


@click.group()
def weft_cli() -> None:
    """Commands for working with .weft binary ephemeris files."""
    pass


@weft_cli.command()
@click.argument("planet", required=True)
@click.argument(
    "quantity", required=True, type=click.Choice([q.name for q in EphemerisQuantity])
)
@click.option(
    "--start-date", "-s", help="Start date (YYYY-MM-DD or Julian date)", required=True
)
@click.option(
    "--end-date", "-e", help="End date (YYYY-MM-DD or Julian date)", required=True
)
@click.option("--output", "-o", help="Output file path", required=True)
@click.option("--data-dir", help="Data directory for cached horizons", default="./data")
@click.option("--prefetch/--no-prefetch", help="Prefetch data", default=True)
@click.option(
    "--prefetch-step", help="Step in hours for prefetching", default=24, type=int
)
def generate(
    planet: str,
    quantity: str,
    start_date: str,
    end_date: str,
    output: str,
    data_dir: str,
    prefetch: bool,
    prefetch_step: int,
) -> None:
    """Generate a .weft binary ephemeris file."""
    # Parse dates
    try:
        start_dt = parse_date_input(start_date)
        end_dt = parse_date_input(end_date)

        # Convert to datetime if it's a Julian date
        if isinstance(start_dt, float):
            from ..space_time.julian import datetime_from_julian

            start_dt = datetime_from_julian(start_dt)
        if isinstance(end_dt, float):
            from ..space_time.julian import datetime_from_julian

            end_dt = datetime_from_julian(end_dt)
    except ValueError as e:
        raise click.BadParameter(f"Invalid date format: {e}")

    # Get the ephemeris quantity
    ephemeris_quantity = None
    for eq in EphemerisQuantity:
        if eq.name == quantity:
            ephemeris_quantity = eq
            break

    if ephemeris_quantity is None:
        raise click.BadParameter(f"Unknown quantity: {quantity}")

    # Ensure output path has extension
    if not output.endswith(".weft"):
        output = f"{output}.weft"

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Generate the file
        file_path = generate_weft_file(
            planet=planet,
            quantity=ephemeris_quantity,
            start_date=start_dt,
            end_date=end_dt,
            output_path=output,
            data_dir=data_dir,
            prefetch=prefetch,
            prefetch_step_hours=prefetch_step,
        )

        click.echo(f"Successfully generated .weft file: {file_path}")
    except Exception as e:
        raise click.ClickException(f"Error generating .weft file: {e}")


@weft_cli.command()
@click.argument("file_path", required=True, type=click.Path(exists=True))
def info(file_path: str) -> None:
    """Display information about a .weft file."""
    from ..weft import WeftReader

    try:
        reader = WeftReader()
        reader.load_file(file_path, "file1")
        file_info = reader.get_info("file1")

        # Display file information
        click.echo(f"File: {file_path}")
        click.echo(f"Preamble: {file_info['preamble']}")
        click.echo(f"Value behavior: {file_info['value_behavior']['type']}")
        if file_info["value_behavior"]["range"]:
            min_val, max_val = file_info["value_behavior"]["range"]
            click.echo(f"Range: [{min_val}, {max_val}]")

        # Block counts
        click.echo(f"Total blocks: {file_info['block_count']}")
        click.echo(f"Multi-year blocks: {file_info['multi_year_blocks']}")
        click.echo(f"Monthly blocks: {file_info['monthly_blocks']}")
        click.echo(f"Daily blocks: {file_info['daily_blocks']}")

        # Date range
        start_date = file_info["start_date"]
        end_date = file_info["end_date"]
        click.echo(f"Date range: {start_date} to {end_date}")

    except Exception as e:
        raise click.ClickException(f"Error reading .weft file: {e}")


@weft_cli.command()
@click.argument("file_path", required=True, type=click.Path(exists=True))
@click.argument("date", required=True)
def lookup(file_path: str, date: str) -> None:
    """Look up a value in a .weft file for a specific date."""
    from ..weft import WeftReader

    try:
        # Parse the date
        dt = parse_date_input(date)

        # Convert to datetime if it's a Julian date
        if isinstance(dt, float):
            from ..space_time.julian import datetime_from_julian

            dt = datetime_from_julian(dt)

        # Read the file
        reader = WeftReader()
        reader.load_file(file_path, "file1")

        # Look up the value
        value = reader.get_value(dt, "file1")

        # Display the value
        click.echo(f"Date: {dt}")
        click.echo(f"Value: {value}")

    except Exception as e:
        raise click.ClickException(f"Error looking up value: {e}")
