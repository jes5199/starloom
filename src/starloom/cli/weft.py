"""
CLI commands for generating and using .weft files.
"""

import click
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from ..weft import generate_weft_file
from ..horizons.quantities import EphemerisQuantity
from .horizons import parse_date_input
from ..weft import WeftReader
from ..weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
)


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
@click.argument("file_path", type=click.Path(exists=True))
def info(file_path: str) -> None:
    """Display information about a .weft file."""
    try:
        reader = WeftReader()
        weft_file = reader.load_file(file_path)
        if weft_file is None:
            raise click.ClickException(f"Failed to load .weft file: {file_path}")

        # Display preamble
        print(f"Preamble: {weft_file.preamble}")

        # Display block counts
        multi_year_blocks = [
            b for b in weft_file.blocks if isinstance(b, MultiYearBlock)
        ]
        monthly_blocks = [b for b in weft_file.blocks if isinstance(b, MonthlyBlock)]
        forty_eight_hour_blocks = [
            b for b in weft_file.blocks if isinstance(b, FortyEightHourBlock)
        ]

        print("\nBlock Summary:")
        print(f"Total blocks: {len(weft_file.blocks)}")
        print(f"Multi-year blocks: {len(multi_year_blocks)}")
        print(f"Monthly blocks: {len(monthly_blocks)}")
        print(f"Forty-eight hour blocks: {len(forty_eight_hour_blocks)}")

        # Display overall date range
        if weft_file.blocks:
            first_block = weft_file.blocks[0]
            last_block = weft_file.blocks[-1]
            if isinstance(first_block, MultiYearBlock):
                start_date = datetime(
                    first_block.start_year, 1, 1, tzinfo=ZoneInfo("UTC")
                )
            elif isinstance(first_block, MonthlyBlock):
                start_date = datetime(
                    first_block.year, first_block.month, 1, tzinfo=ZoneInfo("UTC")
                )
            elif isinstance(first_block, FortyEightHourBlock):
                start_date = datetime(
                    first_block.header.start_day.year,
                    first_block.header.start_day.month,
                    first_block.header.start_day.day,
                    tzinfo=ZoneInfo("UTC"),
                )
            else:
                start_date = datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC"))

            if isinstance(last_block, MultiYearBlock):
                end_date = datetime(
                    last_block.start_year + last_block.duration,
                    1,
                    1,
                    tzinfo=ZoneInfo("UTC"),
                )
            elif isinstance(last_block, MonthlyBlock):
                end_date = datetime(
                    last_block.year,
                    last_block.month,
                    last_block.day_count,
                    tzinfo=ZoneInfo("UTC"),
                )
            elif isinstance(last_block, FortyEightHourBlock):
                end_date = datetime(
                    last_block.header.end_day.year,
                    last_block.header.end_day.month,
                    last_block.header.end_day.day,
                    tzinfo=ZoneInfo("UTC"),
                )
            else:
                end_date = datetime(2100, 1, 1, tzinfo=ZoneInfo("UTC"))

            print(f"\nOverall Date Range: from {start_date} to {end_date}")

        # Display block details
        print("\nBlock Details:")
        for block in weft_file.blocks:
            if isinstance(block, MultiYearBlock):
                print(
                    f"Multi-year block: {block.start_year} to {block.start_year + block.duration} ({len(block.coeffs)} coefficients)"
                )
            elif isinstance(block, MonthlyBlock):
                print(
                    f"Monthly block: {block.year}-{block.month:02d} ({len(block.coeffs)} coefficients)"
                )
            elif isinstance(block, FortyEightHourBlock):
                print(
                    f"48-hour block: {block.header.start_day} ({len(block.coefficients)} coefficients)"
                )
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
