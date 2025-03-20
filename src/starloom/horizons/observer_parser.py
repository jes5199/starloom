"""Observer ephemeris parser for JPL Horizons API responses.

This module provides a parser for JPL Horizons API responses in OBSERVER ephemeris type format.
The parser can handle different column formats and dynamically maps column names to quantity enums.
"""

import csv
from typing import List, Tuple, Dict, Optional
from .quantities import EphemerisQuantity, QuantityForColumnName, normalize_column_name
from ..ephemeris import Quantity


class ObserverParser:
    """Parser for observer ephemeris responses from JPL Horizons.

    This class is designed to handle any column format from Horizons API
    observer ephemeris responses. It dynamically maps column names in the CSV response
    to EphemerisQuantity enum values, handles special cases like blank columns,
    and provides methods to access the parsed data.

    The parser expects the standard Horizons format with $$SOE and $$EOE markers
    delimiting the data section, and CSV-formatted data lines.

    Example:
        parser = ObserverParser(horizons_response)
        jd, values = parser.parse()[0]  # Get first data point
        distance = values.get(EphemerisQuantity.DISTANCE)
        all_distances = parser.get_values(EphemerisQuantity.DISTANCE)
    """

    def __init__(self, response: str):
        """Initialize parser.

        Args:
            response: Response text from Horizons API
        """
        self.response = response
        self._headers = None
        self._column_map = None

    def _extract_csv_lines(self) -> List[str]:
        """Extract CSV lines from the Horizons response.

        The response format is:
        *******************************************************************************
        ... metadata ...
        *******************************************************************************
        JDUT, col1, col2, ... (header line)
        $$SOE
        2460000.500000000, value1, value2, ...  (data lines)
        $$EOE
        *******************************************************************************
        """
        csv_lines = []
        header_line = None
        in_table = False

        for line in self.response.split("\n"):
            # Skip empty lines
            if not line.strip():
                continue

            # End of data section
            if line.startswith("$$EOE"):
                break

            # Start of data section
            if line.startswith("$$SOE"):
                in_table = True
                if header_line:
                    csv_lines.append(header_line)
                continue

            # Store header line if we find one before $$SOE
            if not in_table and "JDUT" in line:
                header_line = line
                continue

            # Store data lines
            if in_table:
                csv_lines.append(line)

        return csv_lines

    def _get_headers(self) -> List[str]:
        """Get headers from the CSV data."""
        if self._headers is None:
            csv_lines = self._extract_csv_lines()
            if not csv_lines:
                self._headers = []
                return []

            reader = csv.reader(csv_lines)
            try:
                self._headers = next(reader)
            except StopIteration:
                self._headers = []

        return self._headers

    def _get_quantity_for_column(
        self, column_name: str, blank_columns_seen: int = 0
    ) -> Optional[EphemerisQuantity]:
        """Map column name to EphemerisQuantity."""
        if column_name.strip() == "":
            # Check how many blank columns we've seen to determine which quantity it represents
            if blank_columns_seen == 0:  # First blank column
                return EphemerisQuantity.SOLAR_PRESENCE_CONDITION_CODE
            elif blank_columns_seen == 1:  # Second blank column
                return EphemerisQuantity.TARGET_EVENT_MARKER
            else:
                return None

        # Direct mapping for JPL Horizons column names to EphemerisQuantity
        normalized_name = normalize_column_name(column_name)
        # First check if it's already an EphemerisQuantity-specific column
        for q in EphemerisQuantity:
            if q.value == normalized_name:
                return q

        # Otherwise check the general Quantity mapping and convert if needed
        quantity = QuantityForColumnName.get(normalized_name, None)
        if quantity is None:
            return None

        # Map between general Quantity and EphemerisQuantity
        # This is a simplified mapping for the most common quantities
        quantity_to_ephemeris_map = {
            Quantity.DELTA: EphemerisQuantity.DISTANCE,
            Quantity.DELTA_DOT: EphemerisQuantity.RANGE_RATE,
            Quantity.ECLIPTIC_LONGITUDE: EphemerisQuantity.ECLIPTIC_LONGITUDE,
            Quantity.ECLIPTIC_LATITUDE: EphemerisQuantity.ECLIPTIC_LATITUDE,
            Quantity.JULIAN_DATE: EphemerisQuantity.JULIAN_DATE,
        }

        return quantity_to_ephemeris_map.get(quantity, None)

    def _map_columns_to_quantities(self) -> Dict[int, EphemerisQuantity]:
        """Maps column indices to their corresponding EphemerisQuantity, handling blank columns."""
        if self._column_map is not None:
            return self._column_map

        headers = self._get_headers()
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

        self._column_map = result
        return result

    def _get_julian_date_column(self) -> Optional[int]:
        """Find the column index for Julian date."""
        col_map = self._map_columns_to_quantities()
        for col_idx, quantity in col_map.items():
            if quantity == EphemerisQuantity.JULIAN_DATE:
                return col_idx
        return None

    def parse(self) -> List[Tuple[float, Dict[EphemerisQuantity, str]]]:
        """Parse response into list of (Julian date, values) tuples.

        Returns:
            List of (Julian date, values) tuples
        """
        data = []
        csv_lines = self._extract_csv_lines()

        if not csv_lines:
            return data

        reader = csv.reader(csv_lines)
        try:
            # Skip the header row (we already processed it)
            next(reader)
        except StopIteration:
            return data

        col_map = self._map_columns_to_quantities()
        jd_col = self._get_julian_date_column()

        if jd_col is None:
            return data

        for row in reader:
            if len(row) <= jd_col:
                continue

            try:
                jd = float(row[jd_col])
            except (ValueError, IndexError):
                continue

            values = {}
            for col_idx, quantity in col_map.items():
                if col_idx < len(row):
                    values[quantity] = row[col_idx].strip()

            data.append((jd, values))

        return data

    def get_value(self, quantity: EphemerisQuantity) -> str:
        """Get value for a specific quantity from the first data point.

        Args:
            quantity: Quantity to get value for

        Returns:
            Value as string

        Raises:
            KeyError: If quantity not found
        """
        data = self.parse()
        if not data:
            raise KeyError(f"Quantity {quantity} not found")
        if quantity not in data[0][1]:
            raise KeyError(f"Quantity {quantity} not found")
        return data[0][1][quantity]

    def get_values(self, quantity: EphemerisQuantity) -> List[Tuple[float, str]]:
        """Get all values for a specific quantity.

        Args:
            quantity: Quantity to get values for

        Returns:
            List of (Julian date, value) tuples

        Raises:
            KeyError: If quantity not found in any data point
        """
        data = self.parse()
        if not data:
            raise KeyError(f"Quantity {quantity} not found")

        result = []
        for jd, values in data:
            if quantity in values:
                result.append((jd, values[quantity]))

        if not result:
            raise KeyError(f"Quantity {quantity} not found in any data point")

        return result

    def get_all_values(self) -> List[Tuple[float, Dict[EphemerisQuantity, str]]]:
        """Get all values for all quantities.

        Returns:
            List of (Julian date, values) tuples
        """
        return self.parse()
