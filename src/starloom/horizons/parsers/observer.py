"""Parser for OBSERVER type Horizons responses."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..quantities import EphemerisQuantity, EphemerisQuantityForColumnName
from .base import BaseHorizonsParser


class ObserverParser(BaseHorizonsParser[EphemerisQuantity]):
    """Parser for OBSERVER type Horizons responses.

    This parser handles the standard ephemeris response format which includes
    observer-target quantities like distance, position, and velocity.
    """

    def parse(self) -> List[Tuple[float, Dict[EphemerisQuantity, str]]]:
        """Parse the OBSERVER type response.

        The response format is:
        *******************************************************************************
        ... metadata ...
        *******************************************************************************
        $$SOE
        2025-Mar-19 20:00:00.000, , , 0.28178474111494, -1.4462092, 4.6578683, 8.5530776,
        $$EOE
        *******************************************************************************

        Returns:
            List of (julian_date, {quantity: value}) tuples
        """
        csv_lines = self._extract_csv_lines()
        if not csv_lines:
            return []

        result = []
        for line in csv_lines:
            # Split the line into values
            values = [v.strip() for v in line.split(",")]

            # First value is the date
            date_str = values[0]

            # Create a mapping of quantities to values
            data = {}
            # Skip first 3 values (date and two empty columns)
            for i, value in enumerate(values[3:], start=3):
                if value:  # Only include non-empty values
                    if i == 3:
                        data[EphemerisQuantity.DISTANCE] = value
                    elif i == 4:
                        data[EphemerisQuantity.ECLIPTIC_LATITUDE] = value
                    elif i == 5:
                        data[EphemerisQuantity.ECLIPTIC_LONGITUDE] = value
                    # Skip the last value as it's not needed

            # Convert date to Julian date
            try:
                # Try parsing as Julian date first
                jd = float(date_str)
            except ValueError:
                # If not a Julian date, parse as datetime and convert
                dt = datetime.strptime(date_str, "%Y-%b-%d %H:%M:%S.%f")
                jd = self._datetime_to_julian(dt)

            data[EphemerisQuantity.JULIAN_DATE] = str(jd)
            result.append((jd, data))

        return result

    def _extract_csv_lines(self) -> List[str]:
        """Extract data lines from the Horizons response.

        Returns:
            List of data lines containing the ephemeris data
        """
        data_lines = []
        in_data = False

        for line in self.response_text.split("\n"):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # End of data section
            if line.startswith("$$EOE"):
                break

            # Start of data section
            if line.startswith("$$SOE"):
                in_data = True
                continue

            # Store data lines
            if in_data:
                data_lines.append(line)

        return data_lines

    def _get_quantity_for_column(
        self, column_name: str, blank_columns_seen: int = 0
    ) -> Optional[EphemerisQuantity]:
        """Get the EphemerisQuantity for a column name.

        Args:
            column_name: The column name to look up
            blank_columns_seen: Number of blank columns seen so far

        Returns:
            The corresponding EphemerisQuantity, or None if not found
        """
        if column_name.strip() == "":
            # Check how many blank columns we've seen to determine which quantity it represents
            if blank_columns_seen == 0:  # First blank column
                return EphemerisQuantity.SOLAR_PRESENCE_CONDITION_CODE
            elif blank_columns_seen == 1:  # Second blank column
                return EphemerisQuantity.TARGET_EVENT_MARKER
            else:
                return None
        return EphemerisQuantityForColumnName.get(column_name.strip(), None)

    def _map_columns_to_quantities(
        self, headers: List[str]
    ) -> Dict[int, EphemerisQuantity]:
        """Maps column indices to their corresponding EphemerisQuantity.

        Args:
            headers: List of column headers

        Returns:
            Dictionary mapping column indices to EphemerisQuantity values
        """
        result = {}
        blank_columns_seen = 0
        for i, header in enumerate(headers):
            if header.strip() == "":
                q = self._get_quantity_for_column(header, blank_columns_seen)
                blank_columns_seen += 1
            else:
                q = self._get_quantity_for_column(header)
            if q is not None:
                result[i] = q
        return result

    def get_value(self, dt: datetime, quantity: EphemerisQuantity) -> Optional[str]:
        """Get a specific value for a given datetime and quantity.

        Args:
            dt: The datetime to get the value for
            quantity: The quantity to get

        Returns:
            The value as a string, or None if not found
        """
        data = self.parse()
        if not data:
            return None

        # Convert input datetime to Julian date
        jd = self._datetime_to_julian(dt)

        # Find the closest data point
        closest_jd = min(data, key=lambda x: abs(x[0] - jd))[0]
        _, values = next(x for x in data if x[0] == closest_jd)
        return values.get(quantity)
