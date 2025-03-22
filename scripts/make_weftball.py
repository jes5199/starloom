#!/usr/bin/env python3
"""
Script to generate a "weftball" for a planet.

This script:
1. Generates decade-by-decade weft files for ecliptic longitude, ecliptic latitude, and distance
2. Combines them into one big file for each quantity
3. Creates a tar.gz archive containing the three files

Usage:
    python -m scripts.make_weftball <planet>

Example:
    python -m scripts.make_weftball mars
"""

import os
import sys
import shutil
import subprocess
import tarfile

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


def get_decade_range(start_date):
    """Extract the decade from a date string like '1990-12-31'"""
    decade = start_date.split("-")[0][:3] + "0s"
    return decade


def create_temp_dir(planet):
    """Create a temporary directory for generated weft files"""
    temp_dir = f"data/temp_{planet}_weft"
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def generate_weft_files(planet, temp_dir):
    """Generate weft files for each decade and quantity"""
    generated_files = {}

    for quantity_name, quantity_label in QUANTITIES.items():
        generated_files[quantity_label] = []

        for start_date, end_date in DECADES:
            decade = get_decade_range(start_date)
            output_file = f"{temp_dir}/{planet}.{quantity_label}.{decade}.weft"

            print(f"Generating {quantity_label} for {planet} ({decade})...")

            cmd = [
                "starloom",
                "weft",
                "generate",
                planet,
                quantity_name,
                "--start",
                start_date,
                "--stop",
                end_date,
                "--output",
                output_file,
                "--data-dir",
                "data",
                "--step",
                "24h",  # Daily steps
            ]

            subprocess.run(cmd, check=True)
            generated_files[quantity_label].append(output_file)

    return generated_files


def combine_weft_files(planet, temp_dir, generated_files):
    """Combine decade files into one file per quantity"""
    combined_files = {}

    for quantity_label, files in generated_files.items():
        # Start with the first file
        combined_file = f"data/{planet}.{quantity_label}.weft"
        shutil.copy(files[0], combined_file)

        # Combine with the rest of the files
        for i in range(1, len(files)):
            timespan = "1900-2100"
            temp_output = f"{temp_dir}/{planet}.{quantity_label}.combined.tmp.weft"

            cmd = [
                "starloom",
                "weft",
                "combine",
                combined_file,
                files[i],
                temp_output,
                "--timespan",
                timespan,
            ]

            subprocess.run(cmd, check=True)

            # Replace the combined file with the new one
            shutil.move(temp_output, combined_file)

        combined_files[quantity_label] = combined_file
        print(f"Created combined file: {combined_file}")

    return combined_files


def create_tarball(planet, combined_files):
    """Create a tar.gz archive of the combined files"""
    tarball_name = f"data/{planet}.weft.tar.gz"

    with tarfile.open(tarball_name, "w:gz") as tar:
        for _, file_path in combined_files.items():
            tar.add(file_path, arcname=os.path.basename(file_path))

    print(f"Created tarball: {tarball_name}")
    return tarball_name


def cleanup(temp_dir):
    """Clean up temporary files"""
    shutil.rmtree(temp_dir)
    print(f"Cleaned up temporary directory: {temp_dir}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.make_weftball <planet>")
        sys.exit(1)

    planet = sys.argv[1].lower()
    print(f"Generating weftball for {planet}...")

    # Create temporary directory
    temp_dir = create_temp_dir(planet)

    try:
        # Generate weft files
        generated_files = generate_weft_files(planet, temp_dir)

        # Combine files
        combined_files = combine_weft_files(planet, temp_dir, generated_files)

        # Create tarball
        tarball = create_tarball(planet, combined_files)

        print(f"Successfully created weftball for {planet}: {tarball}")
    except Exception as e:
        print(f"Error generating weftball: {e}")
        sys.exit(1)
    finally:
        # Clean up
        cleanup(temp_dir)


if __name__ == "__main__":
    main()
