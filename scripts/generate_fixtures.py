#!/usr/bin/env python3
"""Script to generate fixture data for testing."""

import subprocess
from pathlib import Path

# Configuration
FIXTURES_DIR = Path("tests/fixtures")
SINGLE_TIME = "2025-03-19T20:00:00"
START_TIME = "2025-03-19T20:00:00"
STOP_TIME = "2025-03-19T22:00:00"
STEP = "1h"

# Planets to generate data for
PLANETS = {"ecliptic": ["venus", "mars"], "elements": ["mars", "jupiter"]}


def run_command(cmd):
    """Run a command and return its output."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {result.stderr}")
    return result.stdout


def generate_single_time_data(command, planet):
    """Generate data for a single time point."""
    cmd = ["starloom", "horizons", command, planet, "--date", SINGLE_TIME]
    output = run_command(cmd)
    return output


def generate_time_range_data(command, planet):
    """Generate data for a time range."""
    cmd = [
        "starloom",
        "horizons",
        command,
        planet,
        "--start",
        START_TIME,
        "--stop",
        STOP_TIME,
        "--step",
        STEP,
    ]
    output = run_command(cmd)
    return output


def save_fixture(data, command, planet, time_type):
    """Save fixture data as raw text."""
    fixture_dir = FIXTURES_DIR / command
    fixture_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{planet}_{time_type}.txt"
    with open(fixture_dir / filename, "w") as f:
        f.write(data)


def main():
    """Generate all fixture data."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for command, planets in PLANETS.items():
        for planet in planets:
            # Generate single time data
            single_data = generate_single_time_data(command, planet)
            save_fixture(single_data, command, planet, "single")

            # Generate time range data
            range_data = generate_time_range_data(command, planet)
            save_fixture(range_data, command, planet, "range")


if __name__ == "__main__":
    main()
