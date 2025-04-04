#!/usr/bin/env python3
"""
Script to convert all SVG files in data/retrograde_svgs to PNG format.
Skips conversion if a newer PNG already exists.
Uses svgexport (Node.js) for high-quality conversion with proper support for SVG features.
Preserves transparency from the original SVGs.
"""

import os
import sys
import subprocess
from pathlib import Path
from tqdm import tqdm

def get_file_timestamp(filepath):
    """Get the modification timestamp of a file."""
    return os.path.getmtime(filepath)

def should_convert(svg_path, png_path, script_path):
    """Check if we should convert the SVG to PNG.
    
    Args:
        svg_path: Path to the SVG file
        png_path: Path to the PNG file
        script_path: Path to this conversion script
    
    Returns:
        bool: True if conversion is needed, False otherwise
    """
    # Always convert if PNG doesn't exist
    if not png_path.exists():
        return True
    
    # Get timestamps
    svg_time = get_file_timestamp(svg_path)
    png_time = get_file_timestamp(png_path)
    script_time = get_file_timestamp(script_path)
    
    # Convert if:
    # 1. SVG is newer than PNG, or
    # 2. This script is newer than the PNG
    return svg_time > png_time or script_time > png_time

def convert_svg_to_png(svg_path, png_path):
    """Convert an SVG file to PNG using svgexport.
    Preserves transparency from the original SVG.
    
    Args:
        svg_path: Path to input SVG file
        png_path: Path to output PNG file
    """
    try:
        # Use svgexport with a scale factor of 4x for high resolution
        # First argument is input file, second is output file, third is scale factor
        subprocess.run(
            ["svgexport", str(svg_path), str(png_path), "4x"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error converting {svg_path}: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: svgexport not found. Please install with 'npm install -g svgexport'.", file=sys.stderr)
        print("Note: You might need to use 'sudo npm install -g svgexport --unsafe-perm=true' if you encounter permission issues.", file=sys.stderr)
        return False
    return True

def main():
    """Main entry point for the script."""
    # Get the path to this script
    script_path = Path(__file__).resolve()
    
    base_dir = Path("data/retrograde_svgs")
    
    # Find all SVG files
    svg_files = list(base_dir.rglob("*.svg"))
    
    if not svg_files:
        print("No SVG files found in data/retrograde_svgs")
        return
    
    # Create progress bar
    with tqdm(total=len(svg_files), desc="Converting SVGs to PNGs") as pbar:
        for svg_path in svg_files:
            # Create corresponding PNG path
            png_path = svg_path.with_suffix('.png')
            
            # Check if conversion is needed
            if should_convert(svg_path, png_path, script_path):
                if convert_svg_to_png(svg_path, png_path):
                    pbar.set_postfix({"Converting": svg_path.name})
                else:
                    pbar.set_postfix({"Failed": svg_path.name})
            else:
                pbar.set_postfix({"Skipped": svg_path.name})
            
            pbar.update(1)

if __name__ == "__main__":
    main() 