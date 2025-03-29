#!/usr/bin/env python3
"""
Script to convert all SVG files in data/retrograde_svgs to PNG format.
Skips conversion if a newer PNG already exists.
"""

import os
import sys
import subprocess
from pathlib import Path
from tqdm import tqdm

def get_file_timestamp(filepath):
    """Get the modification timestamp of a file."""
    return os.path.getmtime(filepath)

def should_convert(svg_path, png_path):
    """Check if we should convert the SVG to PNG."""
    if not png_path.exists():
        return True
    
    svg_time = get_file_timestamp(svg_path)
    png_time = get_file_timestamp(png_path)
    
    return svg_time > png_time

def convert_svg_to_png(svg_path, png_path):
    """Convert an SVG file to PNG using rsvg-convert."""
    try:
        subprocess.run(
            ["rsvg-convert", "-f", "png", "-o", str(png_path), str(svg_path)],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error converting {svg_path}: {e.stderr}", file=sys.stderr)
        return False
    return True

def main():
    """Main entry point for the script."""
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
            if should_convert(svg_path, png_path):
                if convert_svg_to_png(svg_path, png_path):
                    pbar.set_postfix({"Converting": svg_path.name})
                else:
                    pbar.set_postfix({"Failed": svg_path.name})
            else:
                pbar.set_postfix({"Skipped": svg_path.name})
            
            pbar.update(1)

if __name__ == "__main__":
    main() 