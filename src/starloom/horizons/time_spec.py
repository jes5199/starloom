from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

from starloom.space_time.julian import julian_from_datetime


class TimeSpecType(Enum):
    RANGE = "RANGE"  # start/stop/step
    DATES = "DATES"  # list of specific dates


@dataclass
class TimeSpec:
    """Specification for time parameters in a Horizons request."""

    dates: Optional[List[datetime]] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    step_size: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate time parameters after initialization."""
        if self.dates is not None and len(self.dates) > 100:
            raise ValueError("Maximum of 100 dates allowed")
        if self.start_time is not None and self.stop_time is not None:
            if self.start_time > self.stop_time:
                raise ValueError("Start time must be before stop time")

    def to_params(self) -> Dict[str, str]:
        """Convert time specification to Horizons API parameters.

        Returns:
            Dict[str, str]: Dictionary of parameter names and values
        """
        params: Dict[str, str] = {}

        if self.dates is not None:
            # Convert dates to Julian dates
            julian_dates = [julian_from_datetime(dt) for dt in self.dates]
            params["TLIST"] = ",".join(str(jd) for jd in julian_dates)
        else:
            if self.start_time is not None:
                params["START_TIME"] = self.start_time.strftime("%Y-%m-%dT%H:%M:%S")
            if self.stop_time is not None:
                params["STOP_TIME"] = self.stop_time.strftime("%Y-%m-%dT%H:%M:%S")
            if self.step_size is not None:
                params["STEP_SIZE"] = self.step_size

        return params

    @classmethod
    def from_dates(cls, dates: List[datetime]) -> "TimeSpec":
        """Create TimeSpec from a list of dates.

        Args:
            dates: List of datetime objects

        Returns:
            TimeSpec: New TimeSpec instance
        """
        return cls(dates=dates)

    @classmethod
    def from_range(cls, start: datetime, stop: datetime, step: str) -> "TimeSpec":
        """Create TimeSpec from a time range.

        Args:
            start: Start datetime
            stop: Stop datetime
            step: Step size string (e.g. "1d", "1h", "30m")

        Returns:
            TimeSpec: New TimeSpec instance
        """
        return cls(start_time=start, stop_time=stop, step_size=step)
