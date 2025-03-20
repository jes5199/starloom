from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Union
from enum import Enum

from starloom.space_time.julian import julian_from_datetime


class TimeSpecType(Enum):
    RANGE = "RANGE"  # start/stop/step
    DATES = "DATES"  # list of specific dates


@dataclass
class TimeSpec:
    """Specification for time parameters in a Horizons request."""

    dates: Optional[List[Union[datetime, float]]] = None
    start_time: Optional[Union[datetime, float]] = None
    stop_time: Optional[Union[datetime, float]] = None
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
            # Convert dates to Julian dates if they aren't already
            julian_dates = [
                dt if isinstance(dt, float) else julian_from_datetime(dt)
                for dt in self.dates
            ]
            params["TLIST"] = ",".join(str(jd) for jd in julian_dates)
        else:
            if self.start_time is not None:
                if isinstance(self.start_time, float):
                    params["START_TIME"] = str(self.start_time)
                else:
                    # Format using the format from the Horizons docs: 'YYYY-MMM-DD HH:MM'
                    # Example from docs: '2035-Jul-12 10:17:19.373'
                    params["START_TIME"] = f"'{self.start_time.strftime('%Y-%b-%d %H:%M')}'"
            if self.stop_time is not None:
                if isinstance(self.stop_time, float):
                    params["STOP_TIME"] = str(self.stop_time)
                else:
                    # Format using the format from the Horizons docs: 'YYYY-MMM-DD HH:MM'
                    params["STOP_TIME"] = f"'{self.stop_time.strftime('%Y-%b-%d %H:%M')}'"
            if self.step_size is not None:
                params["STEP_SIZE"] = self.step_size

        return params

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
