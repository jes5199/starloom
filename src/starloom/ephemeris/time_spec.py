from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Union
from enum import Enum


class TimeSpecType(Enum):
    RANGE = "RANGE"  # start/stop/step
    DATES = "DATES"  # list of specific dates


@dataclass
class TimeSpec:
    """General specification for time parameters in ephemeris calculations."""

    dates: Optional[List[Union[datetime, float]]] = None
    start_time: Optional[Union[datetime, float]] = None
    stop_time: Optional[Union[datetime, float]] = None
    step_size: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate time parameters after initialization."""
        if self.start_time is not None and self.stop_time is not None:
            # Convert both to Julian dates for comparison if needed
            start_jd = (
                self.start_time
                if isinstance(self.start_time, float)
                else self.start_time.timestamp() / 86400 + 2440587.5
            )
            stop_jd = (
                self.stop_time
                if isinstance(self.stop_time, float)
                else self.stop_time.timestamp() / 86400 + 2440587.5
            )
            if start_jd > stop_jd:
                raise ValueError("Start time must be before stop time")

    def get_time_points(self) -> List[Union[datetime, float]]:
        """Get all time points represented by this TimeSpec.

        Returns:
            List of datetime objects or Julian dates (floats) representing all time points.
            For a date list, returns the list directly.
            For a range, generates time points based on start, stop, and step size.

        Raises:
            ValueError: If neither dates nor a complete range (start, stop, step) is specified,
                      or if the step size format is invalid.
        """
        if self.dates is not None:
            return self.dates

        if (
            self.start_time is not None
            and self.stop_time is not None
            and self.step_size is not None
        ):
            # Parse step size
            if not self.step_size or len(self.step_size) < 2:
                raise ValueError(
                    "Invalid step size format. Must be like '1d', '1h', '30m'"
                )

            try:
                value = int(self.step_size[:-1])
                if value <= 0:
                    raise ValueError("Step size value must be positive")
            except ValueError as e:
                if "must be positive" in str(e):
                    raise
                raise ValueError(
                    "Invalid step size format. Must be like '1d', '1h', '30m'"
                )

            unit = self.step_size[-1].lower()

            # Convert both times to datetime if they aren't already
            start_dt = (
                datetime.fromtimestamp((self.start_time - 2440587.5) * 86400)
                if isinstance(self.start_time, float)
                else self.start_time
            )
            stop_dt = (
                datetime.fromtimestamp((self.stop_time - 2440587.5) * 86400)
                if isinstance(self.stop_time, float)
                else self.stop_time
            )

            # Calculate step size in timedelta
            if unit == "d":
                delta = timedelta(days=value)
            elif unit == "h":
                delta = timedelta(hours=value)
            elif unit == "m":
                delta = timedelta(minutes=value)
            else:
                raise ValueError(
                    "Step size must end with 'd' (days), 'h' (hours), or 'm' (minutes)"
                )

            # Generate time points
            time_points: List[Union[datetime, float]] = []
            current = start_dt
            while current <= stop_dt:
                # Convert back to Julian date if input was Julian dates
                if isinstance(self.start_time, float):
                    time_points.append(current.timestamp() / 86400 + 2440587.5)
                else:
                    time_points.append(current)
                current += delta

            return time_points

        raise ValueError(
            "Must specify either dates list or complete range (start, stop, step)"
        )

    @classmethod
    def from_dates(cls, dates: List[Union[datetime, float]]) -> "TimeSpec":
        """Create TimeSpec from a list of dates.

        Args:
            dates: List of datetime objects or Julian dates

        Returns:
            TimeSpec: New TimeSpec instance
        """
        return cls(dates=dates)

    @classmethod
    def from_range(
        cls,
        start: Union[datetime, float],
        stop: Union[datetime, float],
        step: str,
    ) -> "TimeSpec":
        """Create TimeSpec from a time range.

        Args:
            start: Start datetime or Julian date
            stop: Stop datetime or Julian date
            step: Step size string (e.g. "1d", "1h", "30m")

        Returns:
            TimeSpec: New TimeSpec instance
        """
        return cls(start_time=start, stop_time=stop, step_size=step)

    def to_julian_days(self) -> List[float]:
        """
        Convert the TimeSpec to a list of Julian dates.

        Returns:
            A list of Julian dates.
        """
        if self.start_time is None or self.stop_time is None or self.step_size is None:
            raise ValueError("TimeSpec is not fully specified")

        if isinstance(self.start_time, datetime) and isinstance(
            self.stop_time, datetime
        ):
            return self._to_julian_days_datetime()
        else:
            return self._to_julian_days_julian()

    def _to_julian_days_datetime(self) -> List[float]:
        """
        Convert the TimeSpec with datetime values to a list of Julian dates.

        Returns:
            A list of Julian dates.
        """
        from ..space_time.julian import julian_from_datetime

        if self.start_time is None or self.stop_time is None or self.step_size is None:
            raise ValueError("TimeSpec is not fully specified")

        if not isinstance(self.start_time, datetime) or not isinstance(
            self.stop_time, datetime
        ):
            raise ValueError("Both start_time and stop_time must be datetime objects")

        # Parse step size
        if not self.step_size or len(self.step_size) < 2:
            raise ValueError("Invalid step size format. Must be like '1d', '1h', '30m'")

        try:
            value = float(self.step_size[:-1])
            if value <= 0:
                raise ValueError("Step size value must be positive")
        except ValueError as e:
            if "must be positive" in str(e):
                raise
            raise ValueError("Invalid step size format. Must be like '1d', '1h', '30m'")

        unit = self.step_size[-1].lower()

        # Calculate step size in timedelta
        if unit == "d":
            delta = timedelta(days=value)
        elif unit == "h":
            delta = timedelta(hours=value)
        elif unit == "m":
            delta = timedelta(minutes=value)
        else:
            raise ValueError(
                "Step size must end with 'd' (days), 'h' (hours), or 'm' (minutes)"
            )

        # Generate Julian dates
        julian_days: List[float] = []
        current = self.start_time
        while current <= self.stop_time:
            julian_days.append(julian_from_datetime(current))
            current += delta

        return julian_days

    def _to_julian_days_julian(self) -> List[float]:
        """
        Convert the TimeSpec with Julian date values to a list of Julian dates.

        Returns:
            A list of Julian dates.
        """
        if self.start_time is None or self.stop_time is None or self.step_size is None:
            raise ValueError("TimeSpec is not fully specified")

        if isinstance(self.start_time, datetime) or isinstance(
            self.stop_time, datetime
        ):
            raise ValueError(
                "Both start_time and stop_time must be Julian dates (float)"
            )

        # Convert both to float if they aren't already
        start_jd = float(self.start_time)
        stop_jd = float(self.stop_time)

        # Parse step size to days
        if not self.step_size or len(self.step_size) < 2:
            raise ValueError("Invalid step size format. Must be like '1d', '1h', '30m'")

        try:
            value = float(self.step_size[:-1])
            if value <= 0:
                raise ValueError("Step size value must be positive")
        except ValueError as e:
            if "must be positive" in str(e):
                raise
            raise ValueError("Invalid step size format. Must be like '1d', '1h', '30m'")

        unit = self.step_size[-1].lower()

        # Calculate step size in days
        if unit == "d":
            step_days = value
        elif unit == "h":
            step_days = value / 24.0
        elif unit == "m":
            step_days = value / (24.0 * 60.0)
        else:
            raise ValueError(
                "Step size must end with 'd' (days), 'h' (hours), or 'm' (minutes)"
            )

        # Generate Julian dates
        julian_days: List[float] = []
        current_jd = start_jd
        while current_jd <= stop_jd:
            julian_days.append(current_jd)
            current_jd += step_days

        return julian_days
