#!/usr/bin/env python3
"""
Script to generate a "weftball" for a planet.

This script:
1. Generates decade-by-decade weft files for ecliptic longitude, ecliptic latitude, and distance
2. Combines them into one big file for each quantity
3. Creates a tar.gz archive containing the three files

Usage:
    python -m scripts.make_weftball <planet> [options]

Example:
    python -m scripts.make_weftball mars
    python -m scripts.make_weftball jupiter --debug  # Enable debug logging
    python -m scripts.make_weftball saturn -v        # Enable verbose (info) logging
    python -m scripts.make_weftball mercury --quiet  # Suppress all but error logs
"""

import os
import sys
import shutil
import subprocess
import tarfile

from src.starloom.weft.logging import get_logger
from src.starloom.cli.common import setup_arg_parser, configure_logging

# Define the quantities we want to generate
QUANTITIES = {
    "ECLIPTIC_LONGITUDE": "longitude",
    "ECLIPTIC_LATITUDE": "latitude",
    "DISTANCE": "distance",
}

# Define the decades to generate (20th and 21st centuries)
DECADES = [
    ("1899-12-31", "1910-01-02"),
    ("1909-12-31", "1920-01-02"),
    ("1919-12-31", "1930-01-02"),
    ("1929-12-31", "1940-01-02"),
    ("1939-12-31", "1950-01-02"),
    ("1949-12-31", "1960-01-02"),
    ("1959-12-31", "1970-01-02"),
    ("1969-12-31", "1980-01-02"),
    ("1979-12-31", "1990-01-02"),
    ("1989-12-31", "2000-01-02"),
    ("1999-12-31", "2010-01-02"),
    ("2009-12-31", "2020-01-02"),
    ("2019-12-31", "2030-01-02"),
    ("2029-12-31", "2040-01-02"),
    ("2039-12-31", "2050-01-02"),
    ("2049-12-31", "2060-01-02"),
    ("2059-12-31", "2070-01-02"),
    ("2069-12-31", "2080-01-02"),
    ("2079-12-31", "2090-01-02"),
    ("2089-12-31", "2100-01-02"),
]

# Set up logger
logger = get_logger(__name__)


def get_decade_range(start_date):
    """Extract the decade from a date string like '1899-12-31' to return '1900s'"""
    year = int(start_date.split("-")[0])
    # For dates like 1899-12-31 that represent the 1900s decade
    if year % 10 == 9:
        year += 1
    decade = (year // 10) * 10
    return f"{decade}s"


def create_temp_dir(planet):
    """Create a temporary directory for generated weft files"""
    temp_dir = f"data/temp_{planet}_weft"
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def generate_weft_files(planet, temp_dir):
    """Generate weft files for all quantities for the planet.

    Args:
        planet: Planet name
        temp_dir: Temporary directory for output

    Returns:
        Dict mapping quantity to generated file paths
    """
    generated_files = {}

    for quantity, file_name in QUANTITIES.items():
        logger.info(f"Generating {quantity} data for {planet}")

        current_decade_files = []
        for decade_start, decade_end in get_decade_range("1700-01-01 00:00"):
            decade_file = os.path.join(
                temp_dir, f"{planet}_{file_name}_{decade_start[:4]}.weft"
            )

            # Skip if file already exists
            if os.path.exists(decade_file):
                logger.info(f"Using existing file: {decade_file}")
                current_decade_files.append(decade_file)
                continue

            # Build command
            cmd = [
                "python",
                "-m",
                "src.starloom.cli.generate_weft",
                "--planet",
                planet,
                "--output",
                decade_file,
                "--quantity",
                quantity,
                "--start",
                f"{decade_start}",
                "--end",
                f"{decade_end}",
            ]

            # Log the command at debug level
            logger.debug(f"Running: {' '.join(cmd)}")

            # Run the command
            try:
                subprocess.run(cmd, check=True)
                current_decade_files.append(decade_file)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error generating {quantity} for {decade_start}: {e}")
                continue

        # Store the list of files for this quantity
        generated_files[quantity] = current_decade_files

    return generated_files


def combine_weft_files(planet, temp_dir, generated_files):
    """Combine the decade files into one file per quantity.

    Args:
        planet: Planet name
        temp_dir: Temporary directory
        generated_files: Dict of quantity -> file paths

    Returns:
        Dict mapping quantity to combined file paths
    """
    combined_files = {}

    for quantity, file_name in QUANTITIES.items():
        decade_files = generated_files.get(quantity, [])
        if not decade_files:
            logger.warning(f"No files found for {quantity}, skipping")
            continue

        logger.info(f"Combining {len(decade_files)} files for {quantity}")

        # Create the combined file name
        combined_file = os.path.join(temp_dir, f"{planet}_{file_name}.weft")

        # Build the command
        cmd = [
            "python",
            "-m",
            "src.starloom.cli.combine_wefts",
            "--output",
            combined_file,
            *decade_files,
        ]

        # Log the command at debug level
        logger.debug(f"Running: {' '.join(cmd)}")

        # Run the command
        try:
            subprocess.run(cmd, check=True)
            combined_files[quantity] = combined_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Error combining files for {quantity}: {e}")

    return combined_files


def create_tarball(planet, combined_files):
    """Create a tarball of the combined files.

    Args:
        planet: Planet name
        combined_files: Dict of quantity -> file paths

    Returns:
        Path to the created tarball
    """
    # Get a list of files to include
    files_to_include = list(combined_files.values())
    if not files_to_include:
        logger.error("No files to include in tarball")
        return None

    # Create the tarball filename
    tarball_name = f"{planet}_weftball.tar.gz"

    logger.info(f"Creating tarball: {tarball_name}")
    logger.debug(f"Including files: {', '.join(files_to_include)}")

    # Create the tarball
    with tarfile.open(tarball_name, "w:gz") as tar:
        for file_path in files_to_include:
            tar.add(file_path, arcname=os.path.basename(file_path))

    return tarball_name


def cleanup(temp_dir):
    """Clean up the temporary directory.

    Args:
        temp_dir: Temporary directory to remove
    """
    logger.info(f"Cleaning up temporary directory: {temp_dir}")
    shutil.rmtree(temp_dir)


def main():
    """Main entry point for the script."""
    # Set up argument parser using common parser from weft.cli
    parser = setup_arg_parser()

    # Add script-specific arguments
    parser.add_argument("planet", help="Planet name to generate data for")
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't remove temporary files after completion",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging based on command line arguments
    configure_logging(vars(args))

    # Main script logic
    planet = args.planet.lower()

    logger.info(f"Generating weftball for {planet}")

    # Create a temporary directory
    temp_dir = create_temp_dir(planet)
    logger.info(f"Using temporary directory: {temp_dir}")

    try:
        # Generate the weft files
        generated_files = generate_weft_files(planet, temp_dir)

        # Combine the files
        combined_files = combine_weft_files(planet, temp_dir, generated_files)

        # Create a tarball
        tarball = create_tarball(planet, combined_files)

        if tarball:
            logger.info(f"Successfully created {tarball}")
        else:
            logger.error("Failed to create tarball")
            return 1
    finally:
        # Clean up
        if not args.no_cleanup:
            cleanup(temp_dir)
        else:
            logger.info(f"Temporary files kept at {temp_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
