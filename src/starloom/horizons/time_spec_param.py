from typing import Dict
from starloom.ephemeris.time_spec import TimeSpec
from starloom.space_time.julian import julian_from_datetime


class HorizonsTimeSpecParam:
    """Horizons-specific parameter formatter for time specifications."""

    def __init__(self, time_spec: TimeSpec):
        self.time_spec = time_spec

    def to_params(self) -> Dict[str, str]:
        """Convert time specification to Horizons API parameters.

        Returns:
            Dict[str, str]: Dictionary of parameter names and values
        """
        params: Dict[str, str] = {}

        if self.time_spec.dates is not None:
            # Convert dates to Julian dates if they aren't already
            julian_dates = [
                dt if isinstance(dt, float) else julian_from_datetime(dt)
                for dt in self.time_spec.dates
            ]
            params["TLIST"] = ",".join(str(jd) for jd in julian_dates)
        else:
            if self.time_spec.start_time is not None:
                if isinstance(self.time_spec.start_time, float):
                    params["START_TIME"] = str(self.time_spec.start_time)
                else:
                    # Format using the format from the Horizons docs: 'YYYY-MMM-DD HH:MM'
                    params["START_TIME"] = (
                        f"'{self.time_spec.start_time.strftime('%Y-%b-%d %H:%M')}'"
                    )
            if self.time_spec.stop_time is not None:
                if isinstance(self.time_spec.stop_time, float):
                    params["STOP_TIME"] = str(self.time_spec.stop_time)
                else:
                    # Format using the format from the Horizons docs: 'YYYY-MMM-DD HH:MM'
                    params["STOP_TIME"] = (
                        f"'{self.time_spec.stop_time.strftime('%Y-%b-%d %H:%M')}'"
                    )
            if self.time_spec.step_size is not None:
                params["STEP_SIZE"] = self.time_spec.step_size

        return params

    def __eq__(self, other: object) -> bool:
        """Compare two HorizonsTimeSpecParam objects for equality.

        Args:
            other: Object to compare with

        Returns:
            bool: True if objects are equal, False otherwise
        """
        if not isinstance(other, HorizonsTimeSpecParam):
            return NotImplemented
        return self.time_spec == other.time_spec
