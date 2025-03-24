"""
Weft-based ephemeris implementation.

This module provides an implementation of the Ephemeris interface
that reads position data from weftball archives (tar.gz or tar files).
"""

import os
import tarfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, List

from starloom.ephemeris import Ephemeris, Quantity
from starloom.ephemeris.time_spec import TimeSpec
from starloom.space_time.julian import datetime_to_julian, julian_to_datetime
from starloom.weft.weft_reader import WeftReader


class WeftEphemeris(Ephemeris):
    """
    Implements the Ephemeris interface using weftball archives.

    This class reads weft files from a tar.gz or tar archive (weftball) without
    extracting them to disk, and provides ephemeris data from them.
    """

    def __init__(self, data_dir: str = "./data", data: Optional[str] = None) -> None:
        """
        Initialize a WeftEphemeris instance.

        Args:
            data_dir: Path to the weftball file or directory containing weftball files
                     (maintained for backward compatibility)
            data: Path to the weftball file or directory containing weftball files
                  (newer parameter name that takes precedence when provided)
        """
        # data parameter takes precedence if provided
        self.data_dir = data if data is not None else data_dir
        self.readers: Dict[str, Dict[str, WeftReader]] = {}

    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
    ) -> Dict[Quantity, Any]:
        """
        Get a planet's position at a specific time.

        Args:
            planet: The name or identifier of the planet
            time_point: The time for which to retrieve the position.
                     If None, the current time is used.
                     Can be a Julian date float or a datetime object.

        Returns:
            A dictionary mapping Quantity enum values to their corresponding values
        """
        # Create a TimeSpec with just this single time point
        if time_point is None:
            time_point = datetime.now(timezone.utc)

        time_spec = TimeSpec.from_dates([time_point])

        # Use the get_planet_positions method to handle the single time point
        positions = self.get_planet_positions(planet, time_spec)

        # Return the position for the single time point
        if positions:
            return next(iter(positions.values()))

        return {}

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """
        Get a planet's positions for multiple times specified by a TimeSpec.

        Args:
            planet: The name or identifier of the planet
            time_spec: Time specification defining the times to retrieve positions for

        Returns:
            A dictionary mapping Julian dates to position data dictionaries
        """
        planet_lower = planet.lower()
        # Ensure we have readers for this planet
        self._ensure_planet_readers(planet_lower)

        # Generate all required Julian dates
        julian_dates = self._get_julian_dates(time_spec)

        result: Dict[float, Dict[Quantity, Any]] = {}

        # For each date, get the position data
        for jd in julian_dates:
            # Convert to datetime for WeftReader
            dt = julian_to_datetime(jd)

            # Get each quantity from the corresponding reader
            position_data: Dict[Quantity, Any] = {}

            # Longitude
            if f"{planet_lower}_longitude" in self.readers.get(planet_lower, {}):
                reader = self.readers[planet_lower][f"{planet_lower}_longitude"]
                try:
                    longitude = reader.get_value(dt)
                    position_data[Quantity.ECLIPTIC_LONGITUDE] = longitude
                except Exception:
                    position_data[Quantity.ECLIPTIC_LONGITUDE] = 0.0

            # Latitude
            if f"{planet_lower}_latitude" in self.readers.get(planet_lower, {}):
                reader = self.readers[planet_lower][f"{planet_lower}_latitude"]
                try:
                    latitude = reader.get_value(dt)
                    position_data[Quantity.ECLIPTIC_LATITUDE] = latitude
                except Exception:
                    position_data[Quantity.ECLIPTIC_LATITUDE] = 0.0

            # Distance
            if f"{planet_lower}_distance" in self.readers.get(planet_lower, {}):
                reader = self.readers[planet_lower][f"{planet_lower}_distance"]
                try:
                    distance = reader.get_value(dt)
                    position_data[Quantity.DELTA] = distance
                except Exception:
                    position_data[Quantity.DELTA] = 0.0

            # Add the data to the result
            result[jd] = position_data

        return result

    def _get_julian_dates(self, time_spec: TimeSpec) -> List[float]:
        """
        Get Julian dates from a TimeSpec.

        This handles both range-based and date-based TimeSpec objects.

        Args:
            time_spec: The TimeSpec to convert to Julian dates

        Returns:
            List of Julian dates
        """
        # If it's a range-based TimeSpec
        if (
            time_spec.start_time is not None
            and time_spec.stop_time is not None
            and time_spec.step_size is not None
        ):
            return time_spec.to_julian_days()

        # If it's a date-based TimeSpec
        elif time_spec.dates is not None:
            # Convert any datetime objects to Julian dates
            julian_dates: List[float] = []
            for date in time_spec.dates:
                if isinstance(date, datetime):
                    julian_dates.append(datetime_to_julian(date))
                else:
                    julian_dates.append(date)
            return julian_dates

        # If it's neither (shouldn't happen if TimeSpec is validated)
        raise ValueError("TimeSpec must contain either dates or start/stop/step values")

    def _ensure_planet_readers(self, planet: str) -> None:
        """
        Ensure we have readers for all required quantities for the given planet.

        Args:
            planet: The planet name (lowercase)
        """
        # If we already have readers for this planet, return
        if planet in self.readers:
            return

        # Initialize readers dictionary for this planet
        self.readers[planet] = {}

        # Check if data_dir is a directory or a specific file
        weftball_path = self.data_dir
        if not (weftball_path.endswith(".tar.gz") or weftball_path.endswith(".tar")):
            # Assume it's a directory containing a weftball for this planet
            # First try .tar.gz
            tar_gz_path = os.path.join(self.data_dir, f"{planet}_weftball.tar.gz")
            tar_path = os.path.join(self.data_dir, f"{planet}_weftball.tar")
            
            if os.path.exists(tar_gz_path):
                weftball_path = tar_gz_path
            elif os.path.exists(tar_path):
                weftball_path = tar_path
            else:
                raise FileNotFoundError(
                    f"Weftball not found: neither {tar_gz_path} nor {tar_path} exists"
                )

        if not os.path.exists(weftball_path):
            raise FileNotFoundError(f"Weftball not found: {weftball_path}")

        # Open the tar file (auto-detect format)
        with tarfile.open(weftball_path, "r") as tar:
            # Expected filenames within the archive
            expected_files = [
                f"{planet}_longitude.weft",
                f"{planet}_latitude.weft",
                f"{planet}_distance.weft",
            ]

            # For each expected file
            for filename in expected_files:
                try:
                    # Extract the file member
                    file_info = tar.getmember(filename)

                    # Read the file into memory
                    file_obj = tar.extractfile(file_info)
                    if file_obj is None:
                        continue

                    # Read the data into a bytes object
                    with file_obj as f:
                        weft_data = f.read()

                    # Create an in-memory file-like object
                    # Create a reader for this weft file
                    reader = WeftReader()

                    # The WeftReader normally reads from a file,
                    # but we need to parse the data from memory.
                    # We'll modify the approach to use from_bytes:
                    with open("temp_weft_file.weft", "wb") as temp_file:
                        temp_file.write(weft_data)

                    # Now load the temporary file
                    reader.load_file("temp_weft_file.weft")
                    os.remove("temp_weft_file.weft")

                    # Store the reader
                    quantity_name = filename[
                        len(planet) + 1 : -5
                    ]  # Extract "longitude", "latitude", etc.
                    self.readers[planet][f"{planet}_{quantity_name}"] = reader

                except Exception as e:
                    # Just log the error and continue
                    print(f"Error loading {filename}: {str(e)}")
                    continue
