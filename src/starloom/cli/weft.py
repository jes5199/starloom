"""
CLI commands for generating and using .weft files.
"""

import click
import os

from ..weft import generate_weft_file
from ..horizons.quantities import EphemerisQuantity
from .horizons import parse_date_input
from ..weft.blocks import MultiYearBlock, MonthlyBlock, FortyEightHourSectionHeader


@click.group()
def weft() -> None:
    """Commands for working with .weft binary ephemeris files."""
    pass


@weft.command()
@click.argument("planet", required=True)
@click.argument(
    "quantity",
    required=True,
    type=click.Choice([q.name for q in EphemerisQuantity]),
    default=EphemerisQuantity.ECLIPTIC_LONGITUDE.name,
)
@click.option(
    "--start", "-s", help="Start date (YYYY-MM-DD or Julian date)", required=True
)
@click.option(
    "--stop", "-e", help="End date (YYYY-MM-DD or Julian date)", required=True
)
@click.option("--output", "-o", help="Output file path", required=True)
@click.option("--data-dir", help="Data directory for cached horizons", default="./data")
@click.option("--prefetch/--no-prefetch", help="Prefetch data", default=True)
@click.option(
    "--step", help="Step in hours for reading from ephemeris", default=1, type=int
)
def generate(
    planet: str,
    quantity: str,
    start: str,
    stop: str,
    output: str,
    data_dir: str,
    prefetch: bool,
    step: int,
) -> None:
    """Generate a .weft binary ephemeris file."""
    print("Starting generation with parameters:")
    print(f"  Planet: {planet}")
    print(f"  Quantity: {quantity}")
    print(f"  Start date: {start}")
    print(f"  End date: {stop}")
    print(f"  Output: {output}")
    print(f"  Data dir: {data_dir}")
    print(f"  Prefetch: {prefetch}")
    print(f"  Step: {step}")

    # Parse dates
    try:
        print("Parsing dates...")
        start_dt = parse_date_input(start)
        end_dt = parse_date_input(stop)

        # Convert to datetime if it's a Julian date
        if isinstance(start_dt, float):
            from ..space_time.julian import datetime_from_julian

            print("Converting start date from Julian...")
            start_dt = datetime_from_julian(start_dt)
        if isinstance(end_dt, float):
            from ..space_time.julian import datetime_from_julian

            print("Converting end date from Julian...")
            end_dt = datetime_from_julian(end_dt)
        print(f"Parsed dates: {start_dt} to {end_dt}")
    except ValueError as e:
        raise click.BadParameter(f"Invalid date format: {e}")

    # Get the ephemeris quantity
    print("Looking up ephemeris quantity...")
    ephemeris_quantity = None
    for eq in EphemerisQuantity:
        if eq.name == quantity:
            ephemeris_quantity = eq
            break

    if ephemeris_quantity is None:
        raise click.BadParameter(f"Unknown quantity: {quantity}")
    print(f"Found ephemeris quantity: {ephemeris_quantity}")

    # Ensure output path has extension
    if not output.endswith(".weft"):
        output = f"{output}.weft"
    print(f"Using output path: {output}")

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output))
    if output_dir and not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Generate the file
        print("Generating .weft file...")
        file_path = generate_weft_file(
            planet=planet,
            quantity=ephemeris_quantity,
            start_date=start_dt,
            end_date=end_dt,
            output_path=output,
            data_dir=data_dir,
            step_hours=step,
        )

        click.echo(f"Successfully generated .weft file: {file_path}")
    except Exception as e:
        print(f"Error during generation: {str(e)}")
        raise click.ClickException(f"Error generating .weft file: {e}")


@weft.command()
@click.argument("file_path", required=True, type=click.Path(exists=True))
def info(file_path: str) -> None:
    """Display information about a .weft file."""
    from ..weft import WeftReader
    from datetime import datetime, timezone

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
        click.echo("\nBlock Summary:")
        click.echo(f"Total blocks: {file_info['block_count']}")
        click.echo(f"Multi-year blocks: {file_info['multi_year_blocks']}")
        click.echo(f"Monthly blocks: {file_info['monthly_blocks']}")
        click.echo(f"Forty-eight hour blocks: {file_info['daily_blocks']}")

        # Date range
        start_date = file_info["start_date"]
        end_date = file_info["end_date"]
        click.echo(f"\nOverall Date Range: {start_date} to {end_date}")

        # Display detailed block information
        click.echo("\nBlock Details:")
        for i, block in enumerate(file_info["blocks"], 1):
            if isinstance(block, MultiYearBlock):
                block_start = datetime(block.start_year, 1, 1, tzinfo=timezone.utc)
                block_end = datetime(
                    block.start_year + block.duration, 1, 1, tzinfo=timezone.utc
                )
                click.echo(f"\n{i}. Multi-year Block:")
                click.echo(f"   Start: {block_start}")
                click.echo(f"   End: {block_end}")
                click.echo(f"   Duration: {block.duration} years")
                click.echo(f"   Coefficients: {len(block.coeffs)}")
            elif isinstance(block, MonthlyBlock):
                block_start = datetime(block.year, block.month, 1, tzinfo=timezone.utc)
                block_end = datetime(
                    block.year, block.month + 1, 1, tzinfo=timezone.utc
                )
                click.echo(f"\n{i}. Monthly Block:")
                click.echo(f"   Start: {block_start}")
                click.echo(f"   End: {block_end}")
                click.echo(f"   Days: {block.day_count}")
                click.echo(f"   Coefficients: {len(block.coeffs)}")
            elif isinstance(block, FortyEightHourSectionHeader):
                click.echo(f"\n{i}. Forty-eight Hour Section Header:")
                click.echo(f"   Start: {block.start_day}")
                click.echo(f"   End: {block.end_day}")
                click.echo(f"   Block Size: {block.block_size} bytes")
                click.echo(f"   Block Count: {block.block_count}")

    except Exception as e:
        raise click.ClickException(f"Error reading .weft file: {e}")


@weft.command()
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
