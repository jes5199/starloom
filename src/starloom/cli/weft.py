"""
CLI commands for generating and using .weft files.
"""

import click
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys
import signal
import traceback
from typing import Any, Optional
import logging

from starloom.weft.blocks.forty_eight_hour_section_header import FortyEightHourSectionHeader

from ..weft import generate_weft_file
from ..horizons.quantities import EphemerisQuantity
from .horizons import parse_date_input
from ..weft import WeftReader
from ..weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    WeftFile,
)
from . import common
from ..weft.logging import get_logger

# Create a logger for this module
logger = get_logger(__name__)


# Add signal handler for SIGINT (Ctrl+C)
def sigint_handler(sig: int, frame: Any) -> None:
    """
    Signal handler for SIGINT that prints a stack trace and local variables
    """
    print("\n\nCaught SIGINT (Ctrl+C). Stack trace:")
    traceback.print_stack(frame)

    print("\nLocal variables in current frame:")
    if frame is not None and hasattr(frame, "f_locals"):
        local_vars = frame.f_locals
        for var_name, var_value in local_vars.items():
            try:
                print(f"  {var_name} = {var_value}")
            except Exception:
                print(f"  {var_name} = <unprintable value>")

    sys.exit(1)


# Register the signal handler
signal.signal(signal.SIGINT, sigint_handler)


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (can be used multiple times: -v, -vv, -vvv)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging (equivalent to -vv)",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress all logging except errors",
)
def weft(verbose: int, debug: bool, quiet: bool) -> None:
    """Commands for working with .weft binary ephemeris files."""
    # Configure logging based on command line arguments
    common.configure_logging(
        {
            "quiet": quiet,
            "debug": debug,
            "verbose": verbose,
        }
    )
    logger.debug("Debug logging enabled")
    logger.debug(f"Verbosity: {verbose}, Debug: {debug}, Quiet: {quiet}")


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
@click.option(
    "--step",
    help="Step size for reading from ephemeris (e.g. '1h' for hourly, '30m' for 30 minutes)",
    default="24h",
    type=str,
)
@click.option(
    "--timespan",
    "-t",
    help="Custom timespan descriptor for the preamble (e.g. '2000s' or '2020-2030')",
    type=str,
)
def generate(
    planet: str,
    quantity: str,
    start: str,
    stop: str,
    output: str,
    data_dir: str,
    step: str,
    timespan: Optional[str],
) -> None:
    """Generate a .weft binary ephemeris file."""
    # Direct debug output to see if it appears
    root_logger = logging.getLogger()
    root_logger.debug("ROOT LOGGER: Starting weft file generation")

    # Test log levels of different loggers
    print(f"Root logger level: {logging.getLevelName(root_logger.level)}")
    print(
        f"Starloom logger level: {logging.getLevelName(logging.getLogger('starloom').level)}"
    )
    print(f"Weft module logger level: {logging.getLevelName(logger.level)}")
    print(
        f"Handler levels: {[logging.getLevelName(h.level) for h in root_logger.handlers]}"
    )
    print(f"Logger is disabled: {logger.disabled}")
    print(f"Logger propagates: {logger.propagate}")

    # Ensure logger is properly configured
    logger.debug("Starting weft file generation")
    logger.debug(
        f"Parameters: planet={planet}, quantity={quantity}, start={start}, stop={stop}"
    )

    print("Starting generation with parameters:")
    print(f"  Planet: {planet}")
    print(f"  Quantity: {quantity}")
    print(f"  Start date: {start}")
    print(f"  End date: {stop}")
    print(f"  Output: {output}")
    print(f"  Data dir: {data_dir}")
    print(f"  Step: {step}")
    if timespan:
        print(f"  Timespan: {timespan}")

    print("Parsing dates...")
    try:
        start_dt = parse_date_input(start)
        end_dt = parse_date_input(stop)

        # Convert to datetime if it's a Julian date
        if isinstance(start_dt, float):
            from ..space_time.julian import datetime_from_julian

            logger.debug("Converting start date from Julian")
            print("Converting start date from Julian...")
            start_dt = datetime_from_julian(start_dt)
        if isinstance(end_dt, float):
            from ..space_time.julian import datetime_from_julian

            logger.debug("Converting end date from Julian")
            print("Converting end date from Julian...")
            end_dt = datetime_from_julian(end_dt)
        logger.debug(f"Parsed dates: {start_dt} to {end_dt}")
        print(f"Parsed dates: {start_dt} to {end_dt}")

        # Get the ephemeris quantity
        logger.debug("Looking up ephemeris quantity")
        print("Looking up ephemeris quantity...")
        ephemeris_quantity = None
        for eq in EphemerisQuantity:
            if eq.name == quantity:
                ephemeris_quantity = eq
                break

        if ephemeris_quantity is None:
            raise click.BadParameter(f"Unknown quantity: {quantity}")
        logger.debug(f"Found ephemeris quantity: {ephemeris_quantity}")
        print(f"Found ephemeris quantity: {ephemeris_quantity}")

        # Ensure output path has extension
        if not output.endswith(".weft"):
            output = f"{output}.weft"
        logger.debug(f"Using output path: {output}")
        print(f"Using output path: {output}")

        # Ensure output directory exists
        output_dir = os.path.dirname(os.path.abspath(output))
        if output_dir and not os.path.exists(output_dir):
            logger.debug(f"Creating output directory: {output_dir}")
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        # Generate the file
        logger.debug("Starting file generation")
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
                custom_timespan=timespan,
            )

            logger.debug(f"Successfully generated .weft file: {file_path}")
            click.echo(f"Successfully generated .weft file: {file_path}")
        except Exception as e:
            logger.error(f"Error during generation: {e}", exc_info=True)
            print("Error during generation:")
            print(traceback.format_exc())
            raise click.ClickException(f"Error generating .weft file: {e}")

    except ValueError as e:
        logger.error(f"Value error: {e}", exc_info=True)
        raise click.ClickException(str(e))


@weft.command()
@click.argument("file_path", type=click.Path(exists=True))
def info(file_path: str) -> None:
    """Display information about a .weft file."""
    logger.debug(f"Reading info for file: {file_path}")
    try:
        reader = WeftReader()
        weft_file = reader.load_file(file_path)
        if weft_file is None:
            raise click.ClickException(f"Failed to load .weft file: {file_path}")

        # Display preamble
        logger.debug("Displaying file preamble")
        print(f"Preamble: {weft_file.preamble.strip()}")

        # Display file size
        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes < 1024:
            size_str = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            size_str = f"{file_size_bytes / 1024:.1f} KB"
        elif file_size_bytes < 1024 * 1024 * 1024:
            size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{file_size_bytes / (1024 * 1024 * 1024):.1f} GB"
        logger.debug(f"File size: {size_str}")
        print(f"{size_str}", end=": ")

        # Display block counts
        multi_year_blocks = [
            b for b in weft_file.blocks if isinstance(b, MultiYearBlock)
        ]
        monthly_blocks = [b for b in weft_file.blocks if isinstance(b, MonthlyBlock)]
        forty_eight_hour_blocks = [
            b for b in weft_file.blocks if isinstance(b, FortyEightHourBlock)
        ]

        block_counts = f"{len(weft_file.blocks)} blocks ({len(multi_year_blocks)} large, {len(monthly_blocks)} monthly, {len(forty_eight_hour_blocks)} days)"
        logger.debug(f"Block counts: {block_counts}")
        print(block_counts)

        # Display block details
        for block in weft_file.blocks:
            if isinstance(block, MultiYearBlock):
                block_info = f"Multi-year block: {block.start_year} +{block.duration} ({len(block.coeffs)} coefficients)"
            elif isinstance(block, MonthlyBlock):
                block_info = f"Monthly block: {block.year}-{block.month:02d} ({len(block.coeffs)} coefficients)"
            elif isinstance(block, FortyEightHourBlock):
                block_info = f"48-hour block: {block.center_date} ({len(block.coefficients)} coefficients)"
            elif isinstance(block, FortyEightHourSectionHeader):
                block_info = f"48-hour section header: {block.start_day} to {block.end_day}"
            logger.debug(f"Block info: {block_info}")
            print(block_info)
    except Exception as e:
        logger.error(f"Error reading .weft file: {e}", exc_info=True)
        raise click.ClickException(f"Error reading .weft file: {e}")


@weft.command()
@click.argument("file_path", required=True, type=click.Path(exists=True))
@click.argument("date", required=True)
def lookup(file_path: str, date: str) -> None:
    """Look up a value in a .weft file for a specific date."""
    logger.debug(f"Looking up value for date {date} in file {file_path}")
    from ..weft import WeftReader

    try:
        # Parse the date
        dt = parse_date_input(date)

        # Convert to datetime if it's a Julian date
        if isinstance(dt, float):
            from ..space_time.julian import datetime_from_julian

            logger.debug("Converting date from Julian")
            dt = datetime_from_julian(dt)

        # Read the file
        reader = WeftReader()
        reader.load_file(file_path, "file1")

        # Look up the value
        value = reader.get_value("file1", dt)

        # Display the value
        logger.debug(f"Found value: {value}")
        click.echo(f"Date: {dt}")
        click.echo(f"Value: {value}")

    except Exception as e:
        logger.error(f"Error looking up value: {e}", exc_info=True)
        raise click.ClickException(f"Error looking up value: {e}")


@weft.command()
@click.argument("file1", type=click.Path(exists=True))
@click.argument("file2", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option(
    "--timespan",
    "-t",
    help="Descriptive timespan (e.g. '2024s' or '2024-2025')",
    required=True,
)
def combine(file1: str, file2: str, output: str, timespan: str) -> None:
    """Combine two .weft files into a single file.

    The input files must have matching preambles (except for timespan and generation timestamp).
    The output file will have a new timespan specified by --timespan.
    """
    logger.debug(f"Combining files {file1} and {file2} into {output}")
    try:
        # Read both files
        reader = WeftReader()
        weft1 = reader.load_file(file1, "file1")
        weft2 = reader.load_file(file2, "file2")

        # Combine the files
        combined = WeftFile.combine(weft1, weft2, timespan)

        # Ensure output path has extension
        if not output.endswith(".weft"):
            output = f"{output}.weft"

        # Ensure output directory exists
        output_dir = os.path.dirname(os.path.abspath(output))
        if output_dir and not os.path.exists(output_dir):
            logger.debug(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        # Save the combined file
        combined.write_to_file(output)
        logger.debug(f"Successfully combined files into: {output}")
        click.echo(f"Successfully combined files into: {output}")

    except Exception as e:
        logger.error(f"Error combining .weft files: {e}", exc_info=True)
        raise click.ClickException(f"Error combining .weft files: {e}")
