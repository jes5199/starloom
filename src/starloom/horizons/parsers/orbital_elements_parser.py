"""Elements ephemeris parser for JPL Horizons API responses.

This module provides a parser for JPL Horizons API responses in ELEMENTS ephemeris type format.
The parser handles the standard column format for orbital elements.
"""

import csv
from typing import List, Tuple, Dict
from enum import Enum


class OrbitalElementsQuantity(Enum):
    """Quantities that appear in Elements ephemeris responses."""

    JULIAN_DATE = "JDTDB"
    CALENDAR_DATE = "Calendar Date (TDB)"
    ECCENTRICITY = "EC"
    PERIAPSIS_DISTANCE = "QR"
    INCLINATION = "IN"
    ASCENDING_NODE_LONGITUDE = "OM"  # Longitude of Ascending Node
    ARGUMENT_OF_PERIAPSIS = "W"
    TIME_OF_PERIAPSIS = "Tp"
    MEAN_MOTION = "N"
    MEAN_ANOMALY = "MA"
    TRUE_ANOMALY = "TA"
    SEMI_MAJOR_AXIS = "A"
    APOAPSIS_DISTANCE = "AD"
    ORBITAL_PERIOD = "PR"


class ElementsParser:
    """Parser for elements ephemeris responses from JPL Horizons.

    This class is designed to handle the standard column format from Horizons API
    elements ephemeris responses. It parses the response into a list of data points,
    with each point containing a Julian date and a dictionary of orbital elements.

    The parser expects the standard Horizons format with $$SOE and $$EOE markers
    delimiting the data section, and CSV-formatted data lines.

    Example:
        parser = ElementsParser(horizons_response)
        jd, values = parser.parse()[0]  # Get first data point
        eccentricity = values.get(OrbitalElementsQuantity.ECCENTRICITY)
        semi_major_axis = values.get(OrbitalElementsQuantity.SEMI_MAJOR_AXIS)
    """

    def __init__(self, response: str):
        """Initialize parser.

        Args:
            response: Response text from Horizons API
        """
        self.response = response
        self._column_map = None

    def _extract_csv_lines(self) -> List[str]:
        """Extract CSV lines from the Horizons response.

        The response format is:
        *******************************************************************************
        ... metadata ...
        *******************************************************************************
        JDTDB, Calendar Date, EC, QR, ... (header line)
        **********************************************************
        $$SOE
        2460000.500000000, ... (data lines)
        $$EOE
        **********************************************************
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
                continue

            # Store header line if we find one before $$SOE
            if not in_table and "JDTDB" in line:
                header_line = line
                csv_lines.append(header_line)
                continue

            # Store data lines
            if in_table:
                csv_lines.append(line)

        return csv_lines

    def _map_columns_to_quantities(
        self, headers: List[str]
    ) -> Dict[int, OrbitalElementsQuantity]:
        """Maps column indices to their corresponding OrbitalElementsQuantity.

        Args:
            headers: List of column headers

        Returns:
            Dictionary mapping column indices to quantities
        """
        if self._column_map is not None:
            return self._column_map

        result = {}

        for i, header in enumerate(headers):
            header = header.strip()
            for quantity in OrbitalElementsQuantity:
                if quantity.value == header:
                    result[i] = quantity
                    break

        self._column_map = result
        return result

    def parse(self) -> List[Tuple[float, Dict[OrbitalElementsQuantity, str]]]:
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
            # Get the header row
            headers = next(reader)
            headers = [h.strip() for h in headers]
        except StopIteration:
            return data

        # Map column indices to quantities
        col_map = self._map_columns_to_quantities(headers)

        # Find column index for Julian date
        jd_col = None
        for col_idx, quantity in col_map.items():
            if quantity == OrbitalElementsQuantity.JULIAN_DATE:
                jd_col = col_idx
                break

        if jd_col is None:
            return data

        # Parse data rows
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

    def get_value(self, quantity: OrbitalElementsQuantity) -> str:
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

    def get_values(self, quantity: OrbitalElementsQuantity) -> List[Tuple[float, str]]:
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

    def get_all_values(self) -> List[Tuple[float, Dict[OrbitalElementsQuantity, str]]]:
        """Get all values for all quantities.

        Returns:
            List of (Julian date, values) tuples
        """
        return self.parse()
