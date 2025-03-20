"""Ephemeris database implementation."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union, Any

from ..horizons.quantities import EphemerisQuantity, Quantity
from ..horizons.time_spec import TimeSpec
from ..space_time.julian import datetime_from_julian

logger = logging.getLogger(__name__)


class EphemerisDatabase:
    """Ephemeris database implementation."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the database.

        Args:
            data_dir: Optional directory to store cached data. If not provided,
                defaults to ~/.starloom/data.
        """
        if data_dir is None:
            data_dir = Path.home() / ".starloom" / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_planet_position(
        self,
        planet: str,
        time_point: Union[float, datetime],
    ) -> Optional[Dict[Quantity, Any]]:
        """Get planet position from cache.

        Args:
            planet: Planet name (e.g. "Mars")
            time_point: Time point to get position at (Julian date or datetime)

        Returns:
            Dict mapping quantities to their values, or None if not found
        """
        # Convert Julian date to datetime if needed
        if isinstance(time_point, float):
            try:
                dt = datetime_from_julian(time_point)
            except Exception as e:
                logger.warning(
                    f"Could not convert Julian date {time_point} to datetime: {e}"
                )
                return None
        else:
            dt = time_point

        # Get the data file path
        data_file = self._get_data_file(planet, dt)
        if not data_file.exists():
            return None

        try:
            # Read the data file
            with open(data_file, "r") as f:
                data = f.read().strip().split("\n")
                if len(data) < 2:  # Need at least header and one data point
                    return None

                # Parse header and data
                header = data[0].strip().split(",")
                values = data[1].strip().split(",")

                # Create result dictionary
                result: Dict[Quantity, Any] = {}
                for h, v in zip(header, values):
                    try:
                        quantity = EphemerisQuantity[h]
                        result[quantity] = v
                    except KeyError:
                        continue

                return result
        except Exception as e:
            logger.error(f"Error reading data file {data_file}: {e}")
            return None

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
    ) -> Optional[Dict[datetime, Dict[Quantity, Any]]]:
        """Get planet positions from cache.

        Args:
            planet: Planet name (e.g. "Mars")
            time_spec: TimeSpec object defining the range

        Returns:
            Dict mapping datetime objects to dicts of quantities and their values,
            or None if not found
        """
        # Get the data file path for the range
        data_file = self._get_range_data_file(planet, time_spec)
        if not data_file.exists():
            return None

        try:
            # Read the data file
            with open(data_file, "r") as f:
                data = f.read().strip().split("\n")
                if len(data) < 2:  # Need at least header and one data point
                    return None

                # Parse header and data
                header = data[0].strip().split(",")
                result: Dict[datetime, Dict[Quantity, Any]] = {}

                # Process each data point
                for line in data[1:]:
                    values = line.strip().split(",")
                    if len(values) != len(header):
                        continue

                    # Get datetime from first column
                    try:
                        dt = datetime.fromisoformat(values[0])
                    except ValueError:
                        continue

                    # Create position dictionary
                    position: Dict[Quantity, Any] = {}
                    for h, v in zip(header[1:], values[1:]):  # Skip datetime column
                        try:
                            quantity = EphemerisQuantity[h]
                            position[quantity] = v
                        except KeyError:
                            continue

                    result[dt] = position

                return result
        except Exception as e:
            logger.error(f"Error reading data file {data_file}: {e}")
            return None

    def store_planet_position(
        self,
        planet: str,
        time_point: Union[float, datetime],
        position: Dict[Quantity, Any],
    ) -> None:
        """Store planet position in cache.

        Args:
            planet: Planet name (e.g. "Mars")
            time_point: Time point to store position at (Julian date or datetime)
            position: Dict mapping quantities to their values
        """
        # Convert Julian date to datetime if needed
        if isinstance(time_point, float):
            try:
                dt = datetime_from_julian(time_point)
            except Exception as e:
                logger.warning(
                    f"Could not convert Julian date {time_point} to datetime: {e}"
                )
                return
        else:
            dt = time_point

        # Get the data file path
        data_file = self._get_data_file(planet, dt)
        data_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Write header and data
            with open(data_file, "w") as f:
                # Write header
                header = [q.name for q in position.keys()]
                f.write(",".join(header) + "\n")

                # Write data
                values = [str(v) for v in position.values()]
                f.write(",".join(values) + "\n")
        except Exception as e:
            logger.error(f"Error writing data file {data_file}: {e}")

    def store_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        positions: Dict[datetime, Dict[Quantity, Any]],
    ) -> None:
        """Store planet positions in cache.

        Args:
            planet: Planet name (e.g. "Mars")
            time_spec: TimeSpec object defining the range
            positions: Dict mapping datetime objects to dicts of quantities and their values
        """
        # Get the data file path for the range
        data_file = self._get_range_data_file(planet, time_spec)
        data_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Write header and data
            with open(data_file, "w") as f:
                # Get all unique quantities
                all_quantities = set()
                for position in positions.values():
                    all_quantities.update(position.keys())

                # Write header
                header = ["datetime"] + [q.name for q in all_quantities]
                f.write(",".join(header) + "\n")

                # Write data
                for dt, position in sorted(positions.items()):
                    values = [dt.isoformat()]
                    for q in all_quantities:
                        values.append(str(position.get(q, "")))
                    f.write(",".join(values) + "\n")
        except Exception as e:
            logger.error(f"Error writing data file {data_file}: {e}")

    def _get_data_file(self, planet: str, dt: datetime) -> Path:
        """Get the data file path for a single time point.

        Args:
            planet: Planet name (e.g. "Mars")
            dt: Datetime object

        Returns:
            Path to the data file
        """
        # Create a directory structure: data_dir/planet/YYYY/MM/DD/HH.csv
        return (
            self.data_dir
            / planet.lower()
            / str(dt.year)
            / f"{dt.month:02d}"
            / f"{dt.day:02d}"
            / f"{dt.hour:02d}.csv"
        )

    def _get_range_data_file(self, planet: str, time_spec: TimeSpec) -> Path:
        """Get the data file path for a time range.

        Args:
            planet: Planet name (e.g. "Mars")
            time_spec: TimeSpec object defining the range

        Returns:
            Path to the data file
        """
        # Create a directory structure: data_dir/planet/YYYY/MM/DD/range.csv
        if time_spec.dates:
            dt = time_spec.dates[0]
        else:
            dt = datetime.now()

        return (
            self.data_dir
            / planet.lower()
            / str(dt.year)
            / f"{dt.month:02d}"
            / f"{dt.day:02d}"
            / "range.csv"
        )
