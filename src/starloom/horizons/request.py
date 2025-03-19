from typing import Dict, Optional
import requests
from enum import Enum

from .quantities import Quantities
from .location import Location
from .time_spec import TimeSpec


class EphemType(Enum):
    OBSERVER = "OBSERVER"
    VECTORS = "VECTORS"
    ELEMENTS = "ELEMENTS"
    SPK = "SPK"
    APPROACH = "APPROACH"


class HorizonsRequest:
    """A request to the JPL Horizons API."""

    def __init__(
        self,
        planet: str,
        location: Optional[Location] = None,
        quantities: Optional[Quantities] = None,
        time_spec: Optional[TimeSpec] = None,
    ) -> None:
        """Initialize a Horizons request.

        Args:
            planet: Target body name or ID
            location: Optional observer location
            quantities: Optional quantities to request
            time_spec: Optional time specification
        """
        self.planet = planet
        self.location = location
        self.quantities = quantities or Quantities()
        self.time_spec = time_spec
        self.params: Dict[str, str] = {}
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.post_url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
        self.max_url_length = 1843  # Determined by find_max_url_length.py
        self.max_tlist_length = 70

    def get_url(self) -> str:
        """Generate the URL for this request.

        Returns:
            str: The complete URL with all parameters
        """
        self.params = self._get_base_params()

        if self.time_spec:
            self.params.update(self.time_spec.to_params())

        # Quote parameter values containing commas or spaces
        quoted_params = {
            k: f"'{v}'" if "," in v or " " in v else v for k, v in self.params.items()
        }

        query = "&".join(f"{k}={v}" for k, v in quoted_params.items())
        return f"{self.base_url}?{query}"

    def _get_base_params(self) -> Dict[str, str]:
        """Get base parameters for the request.

        Returns:
            Dict[str, str]: Dictionary of base parameter names and values
        """
        params: Dict[str, str] = {
            "format": "text",
            "MAKE_EPHEM": "YES",
            "OBJ_DATA": "NO",
            "EPHEM_TYPE": "OBSERVER",
            "ANG_FORMAT": "DEG",
            "TIME_DIGITS": "FRACSEC",
            "EXTRA_PREC": "YES",
            "CSV_FORMAT": "YES",
            "COMMAND": self.planet,
        }

        if self.quantities:
            params["QUANTITIES"] = f"'{self.quantities.to_string()}'"

        if self.location:
            params["CENTER"] = f"'{self.location.to_horizons_format()}'"

        return params

    def make_request(self) -> str:
        """Make the request to the Horizons API.

        Returns:
            str: The response from the API

        Raises:
            requests.RequestException: If the request fails
        """
        url = self.get_url()
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            # Try POST as fallback
            try:
                response = requests.post(url)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e2:
                raise requests.RequestException(
                    f"Both GET and POST requests failed: {str(e)}, {str(e2)}"
                ) from e2

    def _get_time_params(self) -> Dict[str, str]:
        """Get time-related parameters for the request.

        Returns:
            Dict[str, str]: Dictionary of time parameter names and values
        """
        if not self.time_spec:
            return {}
        return self.time_spec.to_params()

    def _make_post_request(self) -> str:
        """Make a POST request when the GET URL would be too long.

        Returns:
            str: The response from the API

        Raises:
            requests.RequestException: If the request fails
        """
        print(f"Requesting POST {self.post_url}")
        post_data = self._format_post_data()

        data = {"format": "text"}
        files = {"input": ("input.txt", post_data)}

        try:
            response = requests.post(self.post_url, data=data, files=files)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e}")
            raise

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
                lines.append(f"{key}='{value}'")

        lines.append("\n")
        return "\n".join(lines)
