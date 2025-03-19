from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    """Represents an observer's location on Earth."""

    latitude: float  # in degrees, positive north
    longitude: float  # in degrees, positive east
    elevation: float = 0.0  # in meters above sea level
    name: Optional[str] = None

    def __post_init__(self):
        """Validate the coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        if self.elevation < -500:  # Dead Sea is about -400m
            raise ValueError("Elevation cannot be less than -500 meters")

    def to_horizons_format(self) -> str:
        """Format location for Horizons API."""
        return f"{self.longitude:.6f},{self.latitude:.6f},{self.elevation:.6f}"
