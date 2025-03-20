"""
Planetary models for local ephemeris calculations.

This module provides models for calculating planetary positions using
simplified mathematical approximations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ...ephemeris.quantities import Quantity


class PlanetaryModel(ABC):
    """
    Abstract base class for planetary position models.

    Different implementations can provide different levels of accuracy
    and computational complexity.
    """

    @abstractmethod
    def calculate_position(self, julian_date: float) -> Dict[Quantity, Any]:
        """
        Calculate the position of a planet at a given Julian date.

        Args:
            julian_date: The Julian date for which to calculate the position.

        Returns:
            A dictionary mapping Quantity enum values to their corresponding values.
            Should include at minimum:
            - Quantity.ECLIPTIC_LONGITUDE
            - Quantity.ECLIPTIC_LATITUDE
            - Quantity.DELTA (distance from Earth)
        """
        pass
