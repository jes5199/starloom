"""
Multi-year block implementation for Weft format.

This block type covers multiple years with a single Chebyshev polynomial.
It is the most space-efficient block type but with lower precision.
Typically used for slow-moving objects like outer planets.
"""

import struct
from datetime import datetime, timezone
from typing import List, BinaryIO
import numpy as np

from .utils import evaluate_chebyshev, _ensure_timezone_aware

class MultiYearBlock:
    """
    A block covering multiple years with a single Chebyshev polynomial.

    This is the most space-efficient block type but with lower precision.
    Typically used for slow-moving objects like outer planets.
    """

    marker = b"\x00\x03"  # Block type marker

    def __init__(self, start_year: int, duration: int, coeffs: List[float]):
        """
        Initialize a multi-year block.

        Args:
            start_year: First year covered by the block
            duration: Number of years covered
            coeffs: Chebyshev polynomial coefficients
        """
        self.start_year = start_year
        self.duration = duration
        self.coeffs = coeffs

    def to_bytes(self) -> bytes:
        """
        Convert the block to binary format.

        Returns:
            Binary representation of the block
        """
        # Format:
        # marker (2 bytes)
        # start_year (2 bytes, signed short)
        # duration (2 bytes, unsigned short)
        # coefficient count (4 bytes, unsigned int)
        # coefficients (4 bytes each, float)
        header = struct.pack(">hhI", self.start_year, self.duration, len(self.coeffs))

        # Pack coefficients
        coeffs_bytes = struct.pack(">" + "f" * len(self.coeffs), *self.coeffs)

        return self.marker + header + coeffs_bytes

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "MultiYearBlock":
        """
        Read a multi-year block from a binary stream.

        Args:
            stream: Binary stream positioned after the marker

        Returns:
            A MultiYearBlock instance
        """
        # Read header
        header = stream.read(8)
        start_year, duration, coeff_count = struct.unpack(">hhI", header)

        # Read coefficients
        coeffs_bytes = stream.read(4 * coeff_count)
        coeffs = list(struct.unpack(">" + "f" * coeff_count, coeffs_bytes))

        return cls(start_year=start_year, duration=duration, coeffs=coeffs)

    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this block's range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within range
        """
        # Ensure timezone awareness
        dt = _ensure_timezone_aware(dt)

        year = dt.year
        return self.start_year <= year < self.start_year + self.duration

    def evaluate(self, dt: datetime) -> float:
        """
        Evaluate the block's polynomial at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The interpolated value

        Raises:
            ValueError: If the datetime is outside the block's range
        """
        # Ensure timezone awareness
        dt = _ensure_timezone_aware(dt)

        if not self.contains(dt):
            raise ValueError(f"Datetime {dt} is outside the block's range")

        # Convert datetime to normalized time in [-1, 1] range
        # x = -1 at start of period
        # x = 1 at end of period

        # Get day of year (1-366)
        dt_tz = dt.tzinfo
        year_start = datetime(dt.year, 1, 1, tzinfo=dt_tz)
        days_in_year = (
            366
            if (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
            else 365
        )
        day_of_year = (dt - year_start).days + 1

        year_float = dt.year + (day_of_year - 1) / days_in_year
        x = 2 * ((year_float - self.start_year) / self.duration) - 1

        # Ensure coefficients are in the correct format
        coeffs = np.array(self.coeffs, dtype=np.float32)
        return evaluate_chebyshev(coeffs, x) 