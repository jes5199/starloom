from typing import Dict, Optional, Union, List
from urllib.parse import urlencode
import hashlib
from pathlib import Path
import logging
import re
import requests
from datetime import datetime

from ..planet import Planet
from .quantities import Quantities
from .location import Location, default_location
from .time_spec import TimeSpec
from .time_spec_param import HorizonsTimeSpecParam
from .ephem_type import EphemType
from .quantities import (
    HorizonsRequestObserverQuantities,
    HorizonsRequestVectorQuantities,
    HorizonsRequestElementsQuantities,
)


class HorizonsRequest:
    """A request to the JPL Horizons API."""

    CACHE_DIR = Path("data/http_cache")
    MAX_CACHE_ENTRIES = 100

    def __init__(
        self,
        planet: Union[str, Planet],
        location: Optional[Union[Location, str]] = None,
        quantities: Optional[Union[Quantities, List[int]]] = None,
        time_spec: Optional[TimeSpec] = None,
        time_spec_param: Optional[HorizonsTimeSpecParam] = None,
        ephem_type: EphemType = EphemType.OBSERVER,
        center: Optional[str] = None,
        use_julian: bool = False,
    ) -> None:
        """Initialize a Horizons request.

        Args:
            planet: Target body name or ID
            location: Optional observer location. Can be a Location object or a string
                     (e.g. '@399' for geocentric or a comma-separated coordinate string)
            quantities: Optional quantities to request
            time_spec: Optional time specification
            time_spec_param: Optional Horizons-specific time parameter formatter
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
        self.time_spec_param = time_spec_param or (
            HorizonsTimeSpecParam(time_spec) if time_spec else None
        )
        self.ephem_type = ephem_type
        self.center = center
        self.use_julian = use_julian
        self.params: Dict[str, str] = {}
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.post_url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
        self.max_url_length = 1843  # Determined by find_max_url_length.py
        self.max_tlist_length = 70

        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from a URL.

        Args:
            url: The URL to cache

        Returns:
            str: A hash of the URL to use as the cache key
        """
        return hashlib.sha256(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get the cache file path for a URL.

        Args:
            url: The URL to cache

        Returns:
            Path: Path to the cache file
        """
        return self.CACHE_DIR / f"{self._get_cache_key(url)}.txt"

    def _cleanup_cache(self) -> None:
        """Clean up old cache entries if we exceed the maximum."""
        cache_files = list(self.CACHE_DIR.glob("*.txt"))
        if len(cache_files) > self.MAX_CACHE_ENTRIES:
            # Sort by modification time, oldest first
            cache_files.sort(key=lambda x: x.stat().st_mtime)
            # Remove oldest files until we're under the limit
            for file in cache_files[: -self.MAX_CACHE_ENTRIES]:
                file.unlink()

    def _get_cached_response(self, url: str) -> Optional[str]:
        """Get cached response for a URL if it exists.

        Args:
            url: The URL to check

        Returns:
            Optional[str]: Cached response if it exists, None otherwise
        """
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            return cache_path.read_text()
        return None

    def _cache_response(self, url: str, response: str) -> None:
        """Cache a response for a URL.

        Args:
            url: The URL to cache
            response: The response to cache
        """
        cache_path = self._get_cache_path(url)
        cache_path.write_text(response)
        self._cleanup_cache()

    def get_url(self) -> str:
        """Get URL for request.

        Returns:
            str: URL for request
        """
        params = self._get_base_params()
        # Convert quantities to string format expected by Horizons
        # Only include quantities when ephem_type is OBSERVER
        if self.ephem_type == EphemType.OBSERVER:
            params["QUANTITIES"] = self.quantities.to_string()
        # Add time parameters
        if self.time_spec_param:
            params.update(self.time_spec_param.to_params())
        if self.use_julian:
            params["CAL_FORMAT"] = "JD"

        # First encode everything except single quotes
        def quote_except_quotes(x: str, *args: str) -> str:
            """Quote URL component, preserving single quotes.

            Args:
                x: String to quote
                *args: Additional arguments (unused)

            Returns:
                Quoted string with preserved single quotes
            """
            if x == "'":
                return x
            return urlencode({"": x}, safe="'")[1:]

        url = f"{self.base_url}?{urlencode(params, quote_via=quote_except_quotes)}"
        if len(url) > self.max_url_length:
            print(f"POST url: {self.post_url}")
        else:
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
            if isinstance(self.location, str):
                # Handle special location strings (like @399 for geocentric)
                if self.location.startswith("@"):
                    params["CENTER"] = self.location
                else:
                    # Assume it's a comma-separated coordinate string or observatory code
                    params["SITE_COORD"] = self.location
            else:
                # It's a Location object
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

        # Check cache first
        cached_response = self._get_cached_response(url)
        if cached_response is not None:
            return cached_response

        # lazy import requests library
        import requests

        # If not in cache, make the request
        response = requests.get(url)
        response.raise_for_status()
        response_text = response.text

        # Cache the response
        self._cache_response(url, response_text)

        return response_text

    def _get_time_params(self) -> Dict[str, str]:
        """Get time-related parameters for the request.

        Returns:
            Dict[str, str]: Dictionary of time parameter names and values
        """
        if self.time_spec_param is None:
            return {}

        params = self.time_spec_param.to_params()
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

        # Add quantities only for OBSERVER ephem type
        if self.ephem_type == EphemType.OBSERVER:
            params["QUANTITIES"] = self.quantities.to_string()

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
            and self.time_spec_param == other.time_spec_param
            and self.ephem_type == other.ephem_type
            and self.center == other.center
            and self.use_julian == other.use_julian
        )
