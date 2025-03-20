"""
Monthly block implementation for Weft format.

This block type covers a single month with a Chebyshev polynomial.
It provides medium precision and is efficient for most use cases.
"""

import struct
from datetime import datetime
from typing import List, BinaryIO
import numpy as np

from .utils import evaluate_chebyshev
from starloom.space_time.pythonic_datetimes import ensure_utc


class MonthlyBlock:
    """
    A block covering a single month with a Chebyshev polynomial.

    This provides medium precision and is efficient for most use cases.
    """

    marker = b"\x00\x00"  # Block type marker

    def __init__(self, year: int, month: int, day_count: int, coeffs: List[float]):
        """
        Initialize a monthly block.

        Args:
            year: Year number
            month: Month number (1-12)
            day_count: Number of days in the month
            coeffs: Chebyshev polynomial coefficients

        Raises:
            ValueError: If month or day_count is invalid
        """
        if not 1 <= month <= 12:
            raise ValueError("Month must be between 1 and 12")
        if not 28 <= day_count <= 31:
            raise ValueError("Day count must be between 28 and 31")

        self.year = year
        self.month = month
        self.day_count = day_count
        self.coeffs = np.array(coeffs, dtype=np.float32)

    def to_bytes(self) -> bytes:
        """
        Convert the block to binary format.

        Returns:
            Binary representation of block
        """
        # Format:
        # marker (2 bytes)
        # year (2 bytes, signed short)
        # month (1 byte, unsigned char)
        # day_count (1 byte, unsigned char)
        # coefficient count (4 bytes, unsigned int)
        # coefficients (4 bytes each, float)
        header = struct.pack(
            ">hBBI", self.year, self.month, self.day_count, len(self.coeffs)
        )
        coeffs_bytes = struct.pack(">" + "f" * len(self.coeffs), *self.coeffs)
        return self.marker + header + coeffs_bytes

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "MonthlyBlock":
        """
        Read a monthly block from a binary stream.

        Args:
            stream: Binary stream positioned after the marker

        Returns:
            A MonthlyBlock instance

        Raises:
            ValueError: If the data format is invalid
        """
        # Read header
        header = stream.read(8)
        if len(header) != 8:
            raise ValueError("Incomplete header data")

        year, month, day_count, coeff_count = struct.unpack(">hBBI", header)

        # Validate coefficient count
        if coeff_count > 1000:  # Reasonable maximum size for monthly blocks
            raise ValueError(f"Invalid coefficient count: {coeff_count}")

        # Read coefficients
        coeffs_bytes = stream.read(4 * coeff_count)
        if len(coeffs_bytes) != 4 * coeff_count:
            raise ValueError("Incomplete coefficient data")

        coeffs = list(struct.unpack(">" + "f" * coeff_count, coeffs_bytes))

        return cls(year=year, month=month, day_count=day_count, coeffs=coeffs)

    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this block's range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within range
        """
        # Ensure timezone awareness
        dt = ensure_utc(dt)

        return dt.year == self.year and dt.month == self.month

    def evaluate(self, dt: datetime) -> float:
        """
        Evaluate the block at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The interpolated value

        Raises:
            ValueError: If the datetime is outside the block's range
        """
        # Ensure timezone awareness
        dt = ensure_utc(dt)

        if not self.contains(dt):
            raise ValueError(f"Datetime {dt} is outside the block's range")

        # Convert datetime to normalized time in [-1, 1] range
        # x = -1 at start of month
        # x = 1 at end of month

        # Create start and end dates for this month
        dt_tz = dt.tzinfo
        start_of_month = datetime(self.year, self.month, 1, tzinfo=dt_tz)

        # Handle December to January transition
        if self.month == 12:
            next_month = datetime(self.year + 1, 1, 1, tzinfo=dt_tz)
        else:
            next_month = datetime(self.year, self.month + 1, 1, tzinfo=dt_tz)

        total_seconds = (next_month - start_of_month).total_seconds()
        seconds_elapsed = (dt - start_of_month).total_seconds()
        x = 2 * (seconds_elapsed / total_seconds) - 1

        return evaluate_chebyshev(self.coeffs, x)
