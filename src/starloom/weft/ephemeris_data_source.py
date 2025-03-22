"""
Data source for Weft file generation that manages ephemeris data.

This module provides a wrapper around ephemeris sources that handles
data fetching and filtering for different Weft block types.
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Union, Dict, Any, cast
import bisect

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris import Quantity
from ..horizons.quantities import EphemerisQuantity, EphemerisQuantityToQuantity
from ..horizons.parsers import OrbitalElementsQuantity
from ..ephemeris.time_spec import TimeSpec
from ..space_time.julian import datetime_from_julian


class EphemerisDataSource:
    """
    A data source that manages ephemeris data for Weft file generation.

    This class handles fetching and filtering data for different block types,
    ensuring efficient data access patterns.
    """

    def __init__(
        self,
        ephemeris: Ephemeris,
        planet_id: str,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
        start_date: datetime,
        end_date: datetime,
        step_hours: Union[int, str] = "24h",
    ):
        """
        Initialize the data source.

        Args:
            ephemeris: The ephemeris source to use
            planet_id: The planet ID to get data for
            quantity: The quantity to get data for
            start_date: Start date for data
            end_date: End date for data
            step_hours: Step size for sampling data. Can be a string like '1h', '30m' or an integer for hours.
        """
        self.ephemeris = ephemeris
        self.planet_id = planet_id
        self.quantity = quantity
        self.start_date = start_date
        self.end_date = end_date

        # Convert step_hours to string format if it's an integer
        if isinstance(step_hours, int):
            self.step_hours_str = f"{step_hours}h"
        else:
            self.step_hours_str = step_hours  # Original format

        # Convert to float hours
        if isinstance(step_hours, str):
            # Parse string like "1h", "30m", etc.
            if "h" in step_hours:
                self.step_hours = float(step_hours.replace("h", ""))
            elif "m" in step_hours:
                self.step_hours = float(step_hours.replace("m", "")) / 60.0
            else:
                # Default to hours if no unit specified
                self.step_hours = float(step_hours)
        else:
            self.step_hours = float(step_hours)

        # Convert EphemerisQuantity to Quantity for data access
        if isinstance(quantity, EphemerisQuantity):
            self.standard_quantity = EphemerisQuantityToQuantity[quantity]
        else:
            # For OrbitalElementsQuantity, we need to handle differently
            # This would need proper implementation depending on how orbital elements are mapped
            # For now just use the original quantity
            self.standard_quantity = cast(Quantity, quantity)

        # Create TimeSpec for data fetching
        self.time_spec = TimeSpec.from_range(
            start=start_date,
            stop=end_date,
            step=self.step_hours_str,
        )

        print(f"Fetching ephemeris data from {start_date} to {end_date}...")

        # Get the raw data with float timestamps
        raw_data = ephemeris.get_planet_positions(planet_id, self.time_spec)

        # Debug: print first data point to see structure
        if raw_data:
            first_timestamp = next(iter(raw_data))
            print("Debug: First data point structure:")
            print(f"Timestamp: {first_timestamp}")
            print(f"Data: {raw_data[first_timestamp]}")
            print(f"Available keys: {list(raw_data[first_timestamp].keys())}")
            print(
                f"Looking for quantity: {self.quantity} (value: {self.quantity.value if hasattr(self.quantity, 'value') else self.quantity})"
            )

        # Convert float timestamps to datetime objects and store in self.data
        self.data: Dict[datetime, Dict[Quantity, Any]] = {}
        for timestamp, values in raw_data.items():
            dt = (
                datetime_from_julian(timestamp)
                if isinstance(timestamp, float)
                else timestamp
            )
            self.data[dt] = values

        # Create sorted list of timestamps for binary search
        self.timestamps = sorted(self.data.keys())

    def get_value_at(self, dt: datetime) -> float:
        """Get the value of the quantity at the given datetime.

        Args:
            dt: The datetime to get the value for.

        Returns:
            The value of the quantity at the given datetime.
        """
        if dt < self.start_date or dt > self.end_date:
            raise ValueError(
                f"Datetime {dt} is outside the range of this data source "
                f"({self.start_date} to {self.end_date})"
            )

        # Find nearest timestamps
        idx = bisect.bisect_left(self.timestamps, dt)

        if idx == 0:
            # Use first value if before first timestamp
            t1 = self.timestamps[0]
            try:
                return float(self.data[t1][self.standard_quantity])
            except KeyError:
                # Debug: print what we have when the error occurs
                print("Debug: KeyError in get_value_at")
                print(
                    f"Looking for quantity: {self.quantity} (value: {self.quantity.value if hasattr(self.quantity, 'value') else self.quantity})"
                )
                print(f"Available data at {t1}: {self.data[t1]}")
                print(f"Available keys: {list(self.data[t1].keys())}")
                raise

        if idx == len(self.timestamps):
            # Use last value if after last timestamp
            t1 = self.timestamps[-1]
            return float(self.data[t1][self.standard_quantity])

        # Interpolate between surrounding timestamps
        t1 = self.timestamps[idx - 1]
        t2 = self.timestamps[idx]

        v1 = float(self.data[t1][self.standard_quantity])
        v2 = float(self.data[t2][self.standard_quantity])

        # Linear interpolation
        total_seconds = (t2 - t1).total_seconds()
        elapsed_seconds = (dt - t1).total_seconds()
        fraction = elapsed_seconds / total_seconds

        return v1 + (v2 - v1) * fraction

    def get_values_in_range(
        self, start: datetime, end: datetime, step_hours: Optional[float] = None
    ) -> List[Tuple[datetime, float]]:
        """
        Get values within a date range at specified intervals.

        Args:
            start: Start datetime
            end: End datetime
            step_hours: Optional step size in hours (defaults to source step_hours)

        Returns:
            List of (datetime, value) tuples
        """
        if step_hours is None:
            step_hours = self.step_hours

        if start < self.start_date:
            start = self.start_date
        if end > self.end_date:
            end = self.end_date

        values = []
        current = start
        while current <= end:
            values.append((current, self.get_value_at(current)))
            current += timedelta(hours=step_hours)

        return values
