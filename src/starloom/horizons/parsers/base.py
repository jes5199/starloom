"""Base class for Horizons response parsers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

from ..quantities import EphemerisQuantity

T = TypeVar("T", bound=EphemerisQuantity)


class BaseHorizonsParser(ABC, Generic[T]):
    """Base class for parsing Horizons API responses.

    This class provides common functionality for parsing different types of
    Horizons responses, such as observer ephemerides and orbital elements.

    Args:
        response_text: The raw response text from the Horizons API
    """

    def __init__(self, response_text: str) -> None:
        """Initialize the parser with response text."""
        self._response_text = response_text
        self._parsed_data: Optional[List[Tuple[float, Dict[T, str]]]] = None

    @property
    def response_text(self) -> str:
        """Get the raw response text."""
        return self._response_text

    @abstractmethod
    def parse(self) -> List[Tuple[float, Dict[T, str]]]:
        """Parse the response text into structured data.

        Returns:
            List of (julian_date, {quantity: value}) tuples
        """
        pass

    def get_value(self, date: datetime, quantity: T) -> Optional[str]:
        """Get a specific value for a date and quantity.

        Args:
            date: The datetime to get the value for
            quantity: The quantity to get the value for

        Returns:
            The value as a string, or None if not found
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse()

        jd = self._datetime_to_julian(date)
        for data_jd, values in self._parsed_data:
            if self._close_enough(data_jd, jd):
                return values.get(quantity)
        return None

    def get_values(self, quantity: T) -> List[Tuple[float, str]]:
        """Get all values for a specific quantity.

        Args:
            quantity: The quantity to get values for

        Returns:
            List of (julian_date, value) tuples
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse()

        result = []
        for jd, values in self._parsed_data:
            if quantity in values:
                result.append((jd, values[quantity]))
        return result

    def get_all_values(self) -> List[Tuple[float, Dict[T, str]]]:
        """Get all values for all quantities.

        Returns:
            List of (julian_date, {quantity: value}) tuples
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse()
        return self._parsed_data

    @staticmethod
    def _close_enough(a: float, b: float) -> bool:
        """Check if two floating point numbers are close enough to be considered equal.

        Args:
            a: First number
            b: Second number

        Returns:
            True if the numbers are close enough
        """
        return abs(a - b) <= 1.16e-08

    @staticmethod
    def _datetime_to_julian(dt: datetime) -> float:
        """Convert datetime to Julian date.

        This implementation follows the algorithm from:
        https://en.wikipedia.org/wiki/Julian_day#Converting_Gregorian_calendar_date_to_Julian_Day_Number

        Args:
            dt: The datetime to convert

        Returns:
            The Julian date
        """
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3

        # Calculate Julian Day Number for the start of the day
        jdn = (
            dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        )

        # Add fractional day
        frac_day = (
            dt.hour / 24.0
            + dt.minute / 1440.0
            + dt.second / 86400.0
            + dt.microsecond / 86400000000.0
        )

        return jdn + frac_day - 0.5  # Subtract 0.5 to align with astronomical JD
