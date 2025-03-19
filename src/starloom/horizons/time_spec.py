from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

from ..space_time import julian

class TimeSpecType(Enum):
    RANGE = "RANGE"  # start/stop/step
    DATES = "DATES"  # list of specific dates

@dataclass
class TimeSpec:
    """A unified way to specify time parameters for Horizons requests."""
    
    type: TimeSpecType
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    step_size: Optional[str] = None
    dates: Optional[List[datetime]] = None
    
    def __post_init__(self):
        """Validate the time specification."""
        if self.type == TimeSpecType.RANGE:
            if not all([self.start_time, self.stop_time, self.step_size]):
                raise ValueError("Range time spec requires start_time, stop_time, and step_size")
        elif self.type == TimeSpecType.DATES:
            if not self.dates:
                raise ValueError("Dates time spec requires at least one date")
    
    @classmethod
    def from_range(cls, start_time: datetime, stop_time: datetime, step_size: str) -> 'TimeSpec':
        """Create a time spec from a range."""
        return cls(
            type=TimeSpecType.RANGE,
            start_time=start_time,
            stop_time=stop_time,
            step_size=step_size
        )
    
    @classmethod
    def from_dates(cls, dates: List[datetime]) -> 'TimeSpec':
        """Create a time spec from a list of dates."""
        return cls(
            type=TimeSpecType.DATES,
            dates=dates
        )
    
    def to_params(self) -> dict:
        """Convert to Horizons API parameters."""
        params = {}
        
        if self.type == TimeSpecType.RANGE:
            params.update({
                "START_TIME": f"JD{julian.julian_from_datetime(self.start_time)}",
                "STOP_TIME": f"JD{julian.julian_from_datetime(self.stop_time)}",
                "STEP_SIZE": self.step_size,
            })
        else:  # DATES
            tlist = sorted(set(julian.julian_from_datetime(d) for d in self.dates))
            params["TLIST"] = ",".join(f"'{item}'" for item in tlist)
        
        return params 