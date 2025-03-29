#!/usr/bin/env python3
"""
Script to generate retrograde graphics for planets using data from knowledge/retrogrades/*.csv
and knowledge/timezones.txt.

This script:
1. Reads retrograde dates from CSV files
2. For each date and timezone, generates a retrograde graphic
3. Outputs commands to stdout before executing them
"""

import os
import sys
import pandas as pd
from tqdm import tqdm
import subprocess

# Define the planets to process
PLANETS = ["mercury", "venus", "mars"]

def read_timezones():
    """Read timezones from knowledge/timezones.txt"""
    with open("knowledge/timezones.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def get_timezone_abbr(timezone):
    """Get city name from timezone"""
    return timezone.split('/')[-1].replace('_', '')

def clean_date(date_str):
    """Clean date string to just YYYY-MM-DD format"""
    # Split on space and take first part to get just the date
    return date_str.split()[0]

def main():
    """Main entry point for the script."""
    # Read timezones
    timezones = read_timezones()
    
    # Create base output directory
    os.makedirs("./data/retrograde_svgs", exist_ok=True)
    
    # Process each planet
    for planet in PLANETS:
        # Read CSV file
        df = pd.read_csv(f"knowledge/retrogrades/{planet}.csv")
        
        # Get total number of iterations for progress bar
        total_iterations = len(df) * len(timezones)
        
        # Create progress bar
        with tqdm(total=total_iterations, desc=f"Processing {planet}") as pbar:
            # Process each date
            for _, row in df.iterrows():
                date = clean_date(row['sun_aspect_date'])
                
                # Process each timezone
                for timezone in timezones:
                    # Build command
                    tz_abbr = get_timezone_abbr(timezone)
                    # Create planet and city subdirectories
                    output_dir = f"./data/retrograde_svgs/{planet}/{tz_abbr}"
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = f"{output_dir}/{planet}-{date}-{tz_abbr}.svg"
                    
                    cmd = [
                        "starloom",
                        "graphics",
                        "retrograde",
                        planet,
                        "--date",
                        f"{date}T20:00:00",
                        "--timezone",
                        timezone,
                        "--output",
                        output_file
                    ]
                    
                    # Print command
                    print(f"Running: {' '.join(cmd)}")
                    
                    # Execute command
                    try:
                        subprocess.run(cmd, check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Error running command: {e}", file=sys.stderr)
                    
                    # Update progress bar
                    pbar.update(1)

if __name__ == "__main__":
    main() 