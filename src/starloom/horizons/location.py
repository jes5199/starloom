from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    """A location on Earth for astronomical observations."""

    latitude: float  # in degrees, positive north
    longitude: float  # in degrees, positive east
    elevation: Optional[float] = None
    name: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        if (
            self.elevation is not None and self.elevation < -500
        ):  # Dead Sea is about -400m
            raise ValueError("Elevation cannot be less than -500 meters")

    def to_horizons_format(self) -> str:
        """Convert location to Horizons API format.

        Returns:
            str: Location in format "longitude,latitude,elevation"
        """
        return f"{self.longitude:.6f},{self.latitude:.6f},{self.elevation:.6f}"

    def __str__(self) -> str:
        """Return string representation of location.

        Returns:
            str: Location in format "lat,lon,elev" with elevation optional
        """
        return self.to_horizons_format()


# Default geocentric location
default_location = Location(
    latitude=0.0, longitude=0.0, elevation=0.0, name="Geocentric"
)
