"""
CLI commands for generating and using .weft files.
"""

import click
import os

from ..weft import generate_weft_file
from ..horizons.quantities import EphemerisQuantity
from .horizons import parse_date_input


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
    "--step",
    help="Step size for reading from ephemeris (e.g. '1h' for hourly, '30m' for 30 minutes)",
    default="24h",
    type=str,
)
def generate(
    planet: str,
    quantity: str,
    start: str,
    stop: str,
    output: str,
    data_dir: str,
    prefetch: bool,
    step: str,
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

    print("Parsing dates...")
    try:
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

        # Generate the file
        print("Generating .weft file...")
        try:
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
            import traceback

            print("Error during generation:")
            print(traceback.format_exc())
            raise click.ClickException(f"Error generating .weft file: {e}")

    except ValueError as e:
        raise click.ClickException(str(e))


@weft.command()
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

        # Count block types
        block_counts = {"multi_year_blocks": 0, "monthly_blocks": 0, "daily_blocks": 0}

        from ..weft import (
            MultiYearBlock,
            MonthlyBlock,
            FortyEightHourBlock,
            FortyEightHourSectionHeader,
        )

        blocks = file_info.get("blocks", [])
        for block in blocks:
            if isinstance(block, MultiYearBlock):
                block_counts["multi_year_blocks"] += 1
            elif isinstance(block, MonthlyBlock):
                block_counts["monthly_blocks"] += 1
            elif isinstance(block, FortyEightHourBlock):
                block_counts["daily_blocks"] += 1

        # Block counts
        click.echo("\nBlock Summary:")
        click.echo(f"Total blocks: {file_info['block_count']}")
        click.echo(f"Multi-year blocks: {block_counts['multi_year_blocks']}")
        click.echo(f"Monthly blocks: {block_counts['monthly_blocks']}")
        click.echo(f"Forty-eight hour blocks: {block_counts['daily_blocks']}")

        # Get date range
        start_date, end_date = reader.get_date_range("file1")
        click.echo(f"\nOverall Date Range: {start_date} to {end_date}")

        # Display detailed block information
        click.echo("\nBlock Details:")
        for block in blocks:
            if isinstance(block, MultiYearBlock):
                click.echo(
                    f"  Multi-year block: {block.start_year} to {block.start_year + block.duration}"
                )
            elif isinstance(block, MonthlyBlock):
                click.echo(f"  Monthly block: {block.year}-{block.month:02d}")
            elif isinstance(block, FortyEightHourSectionHeader):
                # Show just the start day since that's the center of the 48-hour block
                click.echo(f"  48-hour block centered at: {block.start_day}")
            elif isinstance(block, FortyEightHourBlock):
                click.echo(f"    {len(block.coefficients)} coefficients")

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
