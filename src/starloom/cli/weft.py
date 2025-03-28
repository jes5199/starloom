"""
CLI commands for generating and using .weft files.
"""

import click
import os
import sys
import signal
import traceback
from typing import Any, Optional
import logging
import time

from starloom.weft.blocks.forty_eight_hour_section_header import (
    FortyEightHourSectionHeader,
)

from ..weft import generate_weft_file
from .horizons import parse_date_input
from ..weft import WeftReader
from ..weft.weft_file import (
    MultiYearBlock,
    MonthlyBlock,
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
    logger.debug("Debug logging enabled!")
    logger.debug(f"Verbosity: {verbose}, Debug: {debug}, Quiet: {quiet}")


@weft.command()
@click.argument("planet", required=True)
@click.argument(
    "quantity",
    required=True,
    type=click.Choice(["latitude", "longitude", "distance"]),
    default="longitude",
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

        from starloom.horizons.quantities import EphemerisQuantity

        if quantity == "latitude":
            ephemeris_quantity = EphemerisQuantity.ECLIPTIC_LATITUDE
        elif quantity == "longitude":
            ephemeris_quantity = EphemerisQuantity.ECLIPTIC_LONGITUDE
        elif quantity == "distance":
            ephemeris_quantity = EphemerisQuantity.DISTANCE
        else:
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

        # Count forty-eight hour blocks from section headers
        multi_year_blocks = [
            b for b in weft_file.blocks if isinstance(b, MultiYearBlock)
        ]
        monthly_blocks = [b for b in weft_file.blocks if isinstance(b, MonthlyBlock)]
        forty_eight_hour_headers = [
            b for b in weft_file.blocks if isinstance(b, FortyEightHourSectionHeader)
        ]

        # Calculate total 48-hour blocks from headers
        total_48h_blocks = sum(
            header.block_count for header in forty_eight_hour_headers
        )

        block_counts = f"{len(weft_file.blocks) + total_48h_blocks - len(forty_eight_hour_headers)} blocks ({len(multi_year_blocks)} large, {len(monthly_blocks)} monthly, {total_48h_blocks} days)"
        logger.debug(f"Block counts: {block_counts}")
        print(block_counts)

        # Display block details and validate 48-hour sections
        for block in weft_file.blocks:
            if isinstance(block, MultiYearBlock):
                block_info = f"Multi-year block: {block.start_year} +{block.duration} ({len(block.coeffs)} coefficients)"
                logger.debug(f"Block info: {block_info}")
                print(block_info)
            elif isinstance(block, MonthlyBlock):
                block_info = f"Monthly block: {block.year}-{block.month:02d} ({len(block.coeffs)} coefficients)"
                logger.debug(f"Block info: {block_info}")
                print(block_info)
            elif isinstance(block, FortyEightHourSectionHeader):
                block_info = f"48-hour section header: {block.start_day} to {block.end_day} ({block.block_count} blocks)"
                logger.debug(f"Block info: {block_info}")
                print(block_info)

                # For info command, load and display the section blocks
                try:
                    section_blocks = weft_file.get_blocks_in_section(block)
                    actual_block_count = len(section_blocks)

                    # Validate block count
                    if actual_block_count != block.block_count:
                        print("  WARNING: Section has incorrect number of blocks!")
                        print(
                            f"  Expected: {block.block_count}, Found: {actual_block_count}"
                        )

                    for i, section_block in enumerate(section_blocks):
                        if (
                            i < 2 or i >= len(section_blocks) - 2
                        ):  # Show first 2 and last 2 blocks
                            block_info = f"  48-hour block: {section_block.center_date} ({len(section_block.coefficients)} coefficients)"
                            logger.debug(f"Block info: {block_info}")
                            print(block_info)
                        elif i == 2 and len(section_blocks) > 4:
                            print(f"  ... {len(section_blocks) - 4} more blocks ...")
                except Exception as e:
                    print(f"  Error loading section blocks: {e}")
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

        # Show information about parsing
        print(f"Looking up value for {dt} using lazy loading...")

        start_time = time.time()

        # Read the file
        reader = WeftReader()
        reader.load_file(file_path)

        load_time = time.time()
        print(f"File loaded in {load_time - start_time:.3f}s (lazy loading enabled)")

        # Look up the value
        value = reader.get_value(dt)
        lookup_time = time.time()

        # Display the value
        logger.debug(f"Found value: {value}")
        click.echo(f"Date: {dt}")

        # Check if this is an angle quantity
        if reader.file is not None and reader.file.value_behavior["type"] == "wrapping":
            behavior = reader.file.value_behavior
            min_val, max_val = behavior["range"]
            range_size = max_val - min_val

            # Show both wrapped and normalized values
            click.echo(f"Wrapped value: {value}")
            normalized = min_val + ((value - min_val) % range_size)
            click.echo(f"Normalized value: {normalized}")

            # For longitude, also show zodiac sign
            if reader.file.quantity == "ECLIPTIC_LONGITUDE":
                from ..ephemeris.util import get_zodiac_sign

                click.echo(f"Zodiac sign: {get_zodiac_sign(normalized)}")
        else:
            click.echo(f"Value: {value}")

        click.echo(f"Lookup completed in {lookup_time - load_time:.3f}s")
        click.echo(f"Total time: {lookup_time - start_time:.3f}s")

    except Exception as e:
        logger.error(f"Error looking up value: {e}", exc_info=True)
        raise click.ClickException(f"Error looking up value: {e}")


@weft.command()
@click.argument("file_path", required=True, type=click.Path(exists=True))
@click.argument("dates", nargs=-1, required=True)
def lookup_all(file_path: str, dates: tuple[str, ...]) -> None:
    """Look up values from all applicable blocks in a .weft file for specific dates."""
    logger.debug(f"Looking up all values for dates {dates} in file {file_path}")
    from ..weft import WeftReader

    try:
        # Read the file once for all dates
        print(f"Loading file {file_path}...")
        start_time = time.time()
        reader = WeftReader()
        reader.load_file(file_path)
        load_time = time.time()
        print(f"File loaded in {load_time - start_time:.3f}s (lazy loading enabled)")

        # Process each date
        for d in dates:
            try:
                # Parse the date
                dt = parse_date_input(d)

                # Convert to datetime if it's a Julian date
                if isinstance(dt, float):
                    from ..space_time.julian import datetime_from_julian

                    logger.debug("Converting date from Julian")
                    dt = datetime_from_julian(dt)

                # Show information about parsing
                print(f"\nLooking up all values for {dt}...")

                # Look up all values
                lookup_start = time.time()
                values = reader.get_all_values(dt)
                lookup_time = time.time()

                # Display the values
                logger.debug(f"Found values: {values}")
                click.echo(f"Date: {dt}")
                click.echo("Values from each applicable block:")

                # Check if this is an angle quantity
                is_angle = (
                    reader.file is not None
                    and reader.file.value_behavior["type"] == "wrapping"
                )
                if is_angle:
                    behavior = reader.file.value_behavior
                    min_val, max_val = behavior["range"]
                    range_size = max_val - min_val

                for block_type, value in values:
                    if "multi-year" in block_type.lower():
                        # Extract duration from block type string (e.g., "Multi-year block (2000-2009)" -> 10 years)
                        try:
                            years = block_type.split("(")[1].split(")")[0].split("-")
                            duration = int(years[1]) - int(years[0]) + 1
                            block_type = f"{block_type} ({duration} years)"
                        except Exception:
                            pass

                    if is_angle:
                        # Show both wrapped and normalized values
                        click.echo(f"  {block_type}:")
                        click.echo(f"    Wrapped value: {value}")
                        normalized = min_val + ((value - min_val) % range_size)
                        click.echo(f"    Normalized value: {normalized}")

                        # For longitude, also show zodiac sign
                        if reader.file.quantity == "ECLIPTIC_LONGITUDE":
                            from ..ephemeris.util import get_zodiac_sign

                            click.echo(
                                f"    Zodiac sign: {get_zodiac_sign(normalized)}"
                            )
                    else:
                        click.echo(f"  {block_type}: {value}")

                click.echo(f"Lookup completed in {lookup_time - lookup_start:.3f}s")

            except Exception as e:
                logger.error(
                    f"Error looking up values for date {d}: {e}", exc_info=True
                )
                click.echo(f"Error looking up values for date {d}: {e}", err=True)
                continue

        click.echo(f"\nTotal time: {time.time() - start_time:.3f}s")

    except Exception as e:
        logger.error(f"Error loading file: {e}", exc_info=True)
        raise click.ClickException(f"Error loading file: {e}")


@weft.command()
@click.argument("file1", type=click.Path(exists=True))
@click.argument("file2", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--timespan",
    "-t",
    help="Custom timespan descriptor for the preamble (e.g. '2000s' or '2020-2030')",
    type=str,
    required=True,
)
def combine(file1: str, file2: str, output_file: str, timespan: str) -> None:
    """Combine two .weft files into a single file."""
    logger.debug(f"Combining files {file1} and {file2} with timespan {timespan}")
    from ..weft import WeftReader, WeftFile

    try:
        # Read both files
        reader1 = WeftReader()
        reader2 = WeftReader()
        weftA = reader1.load_file(file1)
        weftB = reader2.load_file(file2)

        # Combine the files
        combined = WeftFile.combine(weftA, weftB, timespan)

        # Write the combined file
        combined.write_to_file(output_file)
        logger.debug(f"Wrote combined file to {output_file}")
        click.echo(f"Combined file written to {output_file}")

    except Exception as e:
        logger.error(f"Error combining files: {e}", exc_info=True)
        raise click.ClickException(f"Error combining files: {e}")


@weft.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--lookup-date",
    "-d",
    help="Date to use for lookup benchmark (YYYY-MM-DD)",
    type=str,
)
def load_compare(file_path: str, lookup_date: Optional[str] = None) -> None:
    """Compare lazy loading vs regular loading of a .weft file, and benchmark lookup operations."""
    logger.debug(f"Comparing loading methods for file: {file_path}")
    from ..weft import WeftFile, LazyWeftFile

    try:
        # Get file size for information
        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes < 1024:
            size_str = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            size_str = f"{file_size_bytes / 1024:.1f} KB"
        elif file_size_bytes < 1024 * 1024 * 1024:
            size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{file_size_bytes / (1024 * 1024 * 1024):.1f} GB"

        click.echo(f"Testing file: {file_path} ({size_str})")

        # Read the file data once
        with open(file_path, "rb") as f:
            data = f.read()

        click.echo("File read into memory. Running performance tests...")

        # Test lazy loading
        lazy_start = time.time()
        lazy_file = LazyWeftFile.from_bytes(data)
        lazy_end = time.time()
        lazy_time = lazy_end - lazy_start

        # Count blocks for comparison
        multi_year_blocks = [
            b for b in lazy_file.blocks if isinstance(b, MultiYearBlock)
        ]
        monthly_blocks = [b for b in lazy_file.blocks if isinstance(b, MonthlyBlock)]
        forty_eight_hour_headers = [
            b for b in lazy_file.blocks if isinstance(b, FortyEightHourSectionHeader)
        ]
        total_48h_blocks = sum(
            header.block_count for header in forty_eight_hour_headers
        )

        # Test regular loading
        regular_start = time.time()
        regular_file = WeftFile.from_bytes(data)
        regular_end = time.time()
        regular_time = regular_end - regular_start

        # Report loading results
        improvement = (regular_time - lazy_time) / regular_time * 100

        click.echo("\nLoading Performance Results:")
        click.echo(
            f"File contains: {len(multi_year_blocks)} multi-year blocks, {len(monthly_blocks)} monthly blocks, {total_48h_blocks} forty-eight hour blocks"
        )
        click.echo(f"Lazy loading time:    {lazy_time:.6f}s")
        click.echo(f"Regular loading time: {regular_time:.6f}s")
        click.echo(f"Improvement: {improvement:.2f}%")

        if improvement > 0:
            click.echo(
                "\nLazy loading is faster! This will be especially noticeable for large files with many 48-hour blocks."
            )
        else:
            click.echo(
                "\nRegular loading was faster in this case. This can happen with small files or files with few 48-hour blocks."
            )

        # If lookup date is provided, benchmark lookup operations
        if lookup_date:
            # Parse the lookup date
            try:
                dt = parse_date_input(lookup_date)
                if isinstance(dt, float):
                    from ..space_time.julian import datetime_from_julian

                    dt = datetime_from_julian(dt)

                click.echo(f"\nBenchmarking lookup for date: {dt}")

                # Create WeftReader using the regular file (loads all blocks)
                from ..weft import WeftReader

                reader_regular = WeftReader()
                reader_regular.file = regular_file  # Use the already loaded file

                # Time a lookup using the regular file
                regular_lookup_start = time.time()
                value_regular = reader_regular.get_value(dt)
                regular_lookup_end = time.time()
                regular_lookup_time = regular_lookup_end - regular_lookup_start

                # Create WeftReader using the lazy file (uses binary search)
                reader_lazy = WeftReader()
                reader_lazy.file = lazy_file  # Use the already loaded file

                # Time a lookup using the lazy file with binary search
                lazy_lookup_start = time.time()
                value_lazy = reader_lazy.get_value(dt)
                lazy_lookup_end = time.time()
                lazy_lookup_time = lazy_lookup_end - lazy_lookup_start

                # Report lookup results
                lookup_improvement = (
                    (regular_lookup_time - lazy_lookup_time) / regular_lookup_time * 100
                )
                click.echo("\nLookup Performance Results:")
                click.echo(f"Value from regular lookup: {value_regular}")
                click.echo(f"Value from binary search lookup: {value_lazy}")
                click.echo(f"Regular lookup time: {regular_lookup_time:.6f}s")
                click.echo(f"Binary search lookup time: {lazy_lookup_time:.6f}s")
                click.echo(f"Lookup improvement: {lookup_improvement:.2f}%")

                if lookup_improvement > 0:
                    click.echo(
                        "\nBinary search lookup is faster! This improvement will be more significant for files with many 48-hour blocks."
                    )
                else:
                    click.echo(
                        "\nRegular lookup was faster in this case. This can happen with small files or if binary search overhead exceeds benefits."
                    )

                # Verify binary search produces the same value as regular lookup
                if abs(value_lazy - value_regular) > 1e-10:
                    click.echo(
                        f"\nWarning: Values differ between lookup methods: {value_lazy} vs {value_regular}"
                    )
                    click.echo(f"Difference: {abs(value_lazy - value_regular)}")
                else:
                    click.echo(
                        "\nVerification: Both methods produced the same value (within floating-point precision)."
                    )

            except Exception as e:
                click.echo(f"\nError during lookup benchmark: {e}")

    except Exception as e:
        logger.error(f"Error comparing loading methods: {e}", exc_info=True)
        raise click.ClickException(f"Error comparing loading methods: {e}")
