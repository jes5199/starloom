from typing import Dict, Optional, Union, List
import requests
from urllib.parse import urlencode

from .quantities import Quantities
from .location import Location
from .time_spec import TimeSpec
from .planet import Planet
from .ephem_type import EphemType


class HorizonsRequest:
    """A request to the JPL Horizons API."""

    def __init__(
        self,
        planet: Union[str, Planet],
        location: Optional[Location] = None,
        quantities: Optional[Union[Quantities, List[int]]] = None,
        time_spec: Optional[TimeSpec] = None,
        ephem_type: EphemType = EphemType.OBSERVER,
        center: Optional[str] = None,
        use_julian: bool = False,
    ) -> None:
        """Initialize a Horizons request.

        Args:
            planet: Target body name or ID
            location: Optional observer location
            quantities: Optional quantities to request
            time_spec: Optional time specification
            ephem_type: Type of ephemeris to generate
            center: Optional center body for orbital elements (e.g. '10' for Sun)
            use_julian: Whether to use Julian dates in output
        """
        self.planet = planet
        self.location = location
        self.quantities = (
            Quantities(quantities)
            if isinstance(quantities, list)
            else (quantities or Quantities())
        )
        self.time_spec = time_spec
        self.ephem_type = ephem_type
        self.center = center
        self.use_julian = use_julian
        self.params: Dict[str, str] = {}
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.post_url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
        self.max_url_length = 1843  # Determined by find_max_url_length.py
        self.max_tlist_length = 70

    def get_url(self) -> str:
        """Get URL for request.

        Returns:
            str: URL for request
        """
        params = self._get_base_params()
        # Convert quantities to string format expected by Horizons
        params["QUANTITIES"] = self.quantities.to_string()
        # Add time parameters
        if self.time_spec:
            params.update(self.time_spec.to_params())
            if self.use_julian:
                params["CAL_FORMAT"] = "JD"

        # First encode everything except single quotes
        def quote_except_quotes(x, *args):
            if x == "'":
                return x
            return urlencode({"": x}, safe="'")[1:]

        url = f"{self.base_url}?{urlencode(params, quote_via=quote_except_quotes)}"
        print(f"Request URL: {url}")  # Debug logging
        return url

    def _get_base_params(self) -> Dict[str, str]:
        """Get base parameters for request.

        Returns:
            Dict[str, str]: Base parameters
        """
        params = {
            "format": "text",
            "MAKE_EPHEM": "YES",
            "OBJ_DATA": "NO",
            "EPHEM_TYPE": self.ephem_type.value,
            "ANG_FORMAT": "DEG",
            "TIME_DIGITS": "FRACSEC",
            "EXTRA_PREC": "YES",
            "CSV_FORMAT": "YES",
            "COMMAND": str(
                self.planet.value if isinstance(self.planet, Planet) else self.planet
            ),
        }
        if self.location:
            params["SITE_COORD"] = self.location.to_horizons_format()
        if self.center:
            params["CENTER"] = self.center
        return params

    def make_request(self) -> str:
        """Make request to Horizons API.

        Returns:
            str: Response text
        """
        url = self.get_url()
        if len(url) > self.max_url_length:
            return self._make_post_request()
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _get_time_params(self) -> Dict[str, str]:
        """Get time-related parameters for the request.

        Returns:
            Dict[str, str]: Dictionary of time parameter names and values
        """
        if not self.time_spec:
            return {}
        params = self.time_spec.to_params()
        if self.use_julian:
            params["CAL_FORMAT"] = "JD"
        return params

    def _make_post_request(self) -> str:
        """Make POST request to Horizons API.

        Returns:
            str: Response text
        """
        data = {"format": "text"}
        files = {"input": ("input.txt", self._format_post_data())}
        response = requests.post(self.post_url, data=data, files=files)
        response.raise_for_status()
        return response.text

    def _format_post_data(self) -> str:
        """Format data for POST request.

        Returns:
            str: Formatted data string
        """
        lines = ["!$$SOF"]

        # Add all parameters
        params = {**self._get_base_params(), **self._get_time_params()}
        for key, value in params.items():
            if key != "format":  # Exclude 'format' from the input file
                lines.append(f"{key}={value}")

        lines.append("\n")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        """Compare request with another object.

        Args:
            other: Object to compare with

        Returns:
            bool: True if equal, False otherwise
        """
        if not isinstance(other, HorizonsRequest):
            return NotImplemented
        return (
            self.planet == other.planet
            and self.location == other.location
            and self.quantities == other.quantities
            and self.time_spec == other.time_spec
            and self.ephem_type == other.ephem_type
            and self.center == other.center
            and self.use_julian == other.use_julian
        )
