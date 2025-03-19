from typing import List, Optional
import requests
from urllib.parse import urlencode, quote_plus
import time
from enum import Enum

from ..space_time import julian
from ..ephemeris.quantities import Quantity
from .quantities import RequestQuantityForQuantity
from .planet import Planet
from .location import Location
from .time_spec import TimeSpec, TimeSpecType


class EphemType(Enum):
    OBSERVER = "OBSERVER"
    VECTORS = "VECTORS"
    ELEMENTS = "ELEMENTS"
    SPK = "SPK"
    APPROACH = "APPROACH"


class HorizonsRequest:
    """A class to make requests to the JPL Horizons API."""

    def __init__(
        self,
        planet: Planet,
        location: Optional[Location] = None,
        quantities: Optional[List[Quantity]] = None,
        time_spec: Optional[TimeSpec] = None,
    ):
        """Initialize a Horizons request.

        Args:
            planet: The celestial body to get ephemeris data for
            location: Optional observer location on Earth
            quantities: List of quantities to request
            time_spec: Time specification (either range or dates)
        """
        self.planet = planet
        self.location = location
        self.quantities = quantities or []
        self.time_spec = time_spec

        # Base URL and parameters
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.post_url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
        self.max_url_length = 1843  # Determined by find_max_url_length.py
        self.max_tlist_length = 70

    def _get_base_params(self) -> dict:
        """Get the base parameters for the request."""
        params = {
            "format": "text",
            "MAKE_EPHEM": "YES",
            "OBJ_DATA": "NO",
            "EPHEM_TYPE": EphemType.OBSERVER.value,
            "ANG_FORMAT": "DEG",
            "TIME_DIGITS": "FRACSEC",
            "EXTRA_PREC": "YES",
            "CSV_FORMAT": "YES",
            "COMMAND": self.planet.value,
        }

        # Add location if specified
        if self.location:
            params.update(
                {
                    "CENTER": f"coord@{Planet.EARTH.value}",
                    "SITE_COORD": self.location.to_horizons_format(),
                    "COORD_TYPE": "GEODETIC",
                }
            )

        # Add quantities if specified
        if self.quantities:
            qs = set(self.quantities)
            rqs = [RequestQuantityForQuantity[q] for q in qs]
            ints = sorted(set(rq.value for rq in rqs if rq is not None))
            if ints:
                params["QUANTITIES"] = ",".join(map(str, ints))

        return params

    def _get_time_params(self) -> dict:
        """Get the time-related parameters for the request."""
        if not self.time_spec:
            return {}
        return self.time_spec.to_params()

    def _make_request(self) -> str:
        """Make the request to the Horizons API."""
        get_url = self.get_url()

        if len(get_url) > self.max_url_length or (
            self.time_spec
            and self.time_spec.type == TimeSpecType.DATES
            and len(self.time_spec.dates) > self.max_tlist_length
        ):
            return self._make_post_request()

        print(f"Requesting GET {get_url}")
        response = requests.get(get_url)
        response.raise_for_status()
        return response.text

    def make_request(self) -> str:
        """Make the request with retries."""
        max_retries = 100
        delay = 1  # Initial delay in seconds
        maximum_delay = 60

        for attempt in range(max_retries):
            try:
                return self._make_request()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"Waiting {delay} seconds before retrying...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    if delay > maximum_delay:
                        delay = maximum_delay
                else:
                    print("Max retries reached. Raising exception.")
                    raise
            except Exception as e:
                print(f"Error making request: {e}")
                raise

    def _make_post_request(self) -> str:
        """Make a POST request when the GET URL would be too long."""
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
        """Format the data for a POST request."""
        lines = ["!$$SOF"]

        # Add all parameters
        params = {**self._get_base_params(), **self._get_time_params()}
        for key, value in params.items():
            if key != "format":  # Exclude 'format' from the input file
                lines.append(f"{key}='{value}'")

        # Handle TLIST separately if using dates
        if self.time_spec and self.time_spec.type == TimeSpecType.DATES:
            for d in self.time_spec.dates:
                jd = julian.julian_from_datetime(d)
                lines.append(f"TLIST='{jd}'")

        lines.append("\n")
        return "\n".join(lines)

    def get_url(self) -> str:
        """Get the URL for a GET request."""
        params = {**self._get_base_params(), **self._get_time_params()}

        # Quote values that contain commas or spaces
        for key, value in params.items():
            if isinstance(value, str):
                if "," in value or " " in value:
                    if not (value.startswith("'") and value.endswith("'")):
                        params[key] = f"'{value}'"

        # URL encode the parameters
        query_string = urlencode(params, quote_via=quote_plus)
        return f"{self.base_url}?{query_string}"


class HorizonsSolarRequest(HorizonsRequest):
    def __init__(self, latitude: float, longitude: float, elevation: float = 0):
        super().__init__(Planet.SUN)
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation

    def configure_request(self, req: HorizonsRequest):
        super().configure_request(req)
        # Set coordinates for the observer on Earth
        req.params["CENTER"] = f"coord@{Planet.EARTH.value}"
        req.params["SITE_COORD"] = f"{self.longitude},{self.latitude},{self.elevation}"
        req.params["COORD_TYPE"] = "GEODETIC"
        req.params["QUANTITIES"] = "4,7,34,42"
        req.params["APPARENT"] = "REFRACTED"

        # req.params["OBJ_DATA"] = "YES"
        req.params["SUPPRESS_RANGE_RATE"] = "NO"
