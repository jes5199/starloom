"""Horizons client implementation."""

import logging
from typing import List, Optional

from .quantities import EphemerisQuantity
from .time_spec import TimeSpec
from .time_spec_param import HorizonsTimeSpecParam
from .request import HorizonsRequest
from .ephem_type import EphemType

logger = logging.getLogger(__name__)


class HorizonsClient:
    """Horizons client implementation."""

    def __init__(self):
        """Initialize the client."""
        self.geocentric_location = "@399"  # Special Horizons syntax for center of Earth

    def get_ephemeris(
        self,
        planet: str,
        time_spec: TimeSpec,
        quantities: Optional[List[EphemerisQuantity]] = None,
    ) -> str:
        """Get ephemeris data from Horizons.

        Args:
            planet: Planet name (e.g. "Mars")
            time_spec: TimeSpec object defining the time(s)
            quantities: Optional list of quantities to request. If not provided,
                defaults to DISTANCE, RANGE_RATE, ECLIPTIC_LONGITUDE, ECLIPTIC_LATITUDE.

        Returns:
            Raw response from Horizons API
        """
        if quantities is None:
            quantities = [
                EphemerisQuantity.DISTANCE,
                EphemerisQuantity.RANGE_RATE,
                EphemerisQuantity.ECLIPTIC_LONGITUDE,
                EphemerisQuantity.ECLIPTIC_LATITUDE,
            ]

        # Create request with Horizons-specific time parameter formatting
        request = HorizonsRequest(
            planet=planet,
            location=self.geocentric_location,
            quantities=quantities,
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.OBSERVER,
            use_julian=True,
        )

        # Make request
        try:
            response = request.make_request()
            logger.debug(f"Got response from Horizons for {planet}")
            return response
        except Exception as e:
            logger.error(f"Error getting ephemeris data from Horizons: {e}")
            raise
