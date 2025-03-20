from dataclasses import dataclass
from datetime import datetime
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
