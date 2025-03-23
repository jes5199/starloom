"""
FortyEightHourBlock class for handling 48-hour periods with Chebyshev polynomials.
"""

import struct
from datetime import datetime, timezone, date, time, timedelta
from typing import List, BinaryIO

from .forty_eight_hour_section_header import FortyEightHourSectionHeader
from .utils import evaluate_chebyshev


class FortyEightHourBlock:
    """A block containing coefficients for a 48-hour period."""

    marker = b"\x00\x01"  # Block type marker

    def __init__(self, header: FortyEightHourSectionHeader, coeffs: List[float], center_date: date = None):
        """
        Initialize a forty-eight hour block.

        Args:
            header: The section header
            coeffs: Chebyshev polynomial coefficients
            center_date: The center date of this block (midnight GMT of the specified day)

        Raises:
            ValueError: If any coefficient is NaN
        """
        self.header = header
        self.center_date = center_date

        # Check for NaN values
        if any(
            c != c for c in coeffs
        ):  # NaN is the only value that is not equal to itself
            raise ValueError("Coefficients cannot be NaN")

        # If coefficients list is empty, use a single zero coefficient
        if not coeffs:
            coeffs = [0.0]

        # Strip trailing zeros to get significant coefficients
        while len(coeffs) > 1 and coeffs[-1] == 0:
            coeffs = coeffs[:-1]

        self.coefficients = coeffs

        # Pad to header's count for binary format
        self._full_coeffs = coeffs + [0.0] * (
            self.header.coefficient_count - len(coeffs)
        )

    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this block's range (±24 hours from center).

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within range
        """
        if self.center_date is None:
            # Fallback to section header check if center_date not available
            return self.header.contains_datetime(dt)
            
        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
            
        # Create datetime at midnight UTC for the center date
        center_dt = datetime.combine(self.center_date, time(0, 0), timezone.utc)
        
        # Check if dt is within ±24 hours of center_dt
        delta = dt - center_dt
        return abs(delta.total_seconds()) <= 24 * 60 * 60

    def to_bytes(self) -> bytes:
        """
        Convert the block to binary format.

        Returns:
            Binary representation of block
            
        Raises:
            ValueError: If center_date is not set
        """
        if self.center_date is None:
            raise ValueError("center_date must be set before converting to bytes")
            
        # Start with the marker
        result = bytearray(self.marker)
        
        # Add center date information
        result.extend(struct.pack(">H", self.center_date.year))  # 2 bytes for year
        result.extend(struct.pack(">B", self.center_date.month)) # 1 byte for month
        result.extend(struct.pack(">B", self.center_date.day))   # 1 byte for day
        
        # Add coefficients
        for coeff in self._full_coeffs:
            result.extend(struct.pack(">f", float(coeff)))
            
        return bytes(result)

    @classmethod
    def from_stream(
        cls, stream: BinaryIO, header: FortyEightHourSectionHeader
    ) -> "FortyEightHourBlock":
        """
        Read a forty-eight hour block from a binary stream.

        Args:
            stream: Binary stream positioned after the marker
            header: The section header for this block

        Returns:
            A FortyEightHourBlock instance
        """
        # Read the center date information
        try:
            year = struct.unpack(">H", stream.read(2))[0]  # 2 bytes for year
            month = struct.unpack(">B", stream.read(1))[0]  # 1 byte for month
            day = struct.unpack(">B", stream.read(1))[0]    # 1 byte for day
            center_date = date(year, month, day)
        except (struct.error, ValueError) as e:
            raise ValueError(f"Invalid date data: {str(e)}")

        # Read coefficient data
        coeffs_bytes = stream.read(4 * header.coefficient_count)
        if len(coeffs_bytes) != 4 * header.coefficient_count:
            raise ValueError("Incomplete coefficient data")

        coeffs = []
        for i in range(0, len(coeffs_bytes), 4):
            coeff = struct.unpack(">f", coeffs_bytes[i : i + 4])[0]
            coeffs.append(coeff)

        return cls(header=header, coeffs=coeffs, center_date=center_date)

    def evaluate(self, dt: datetime) -> float:
        """
        Evaluate the block's polynomial at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The interpolated value

        Raises:
            ValueError: If the datetime is outside the block's range or has no timezone
        """
        if dt.tzinfo is None:
            raise ValueError("Datetime must have timezone information")

        if not self.contains(dt):
            raise ValueError("Datetime outside block's range")

        dt = dt.astimezone(timezone.utc)
        
        if self.center_date is not None:
            # Calculate x based on hours from center date
            center_dt = datetime.combine(self.center_date, time(0, 0), timezone.utc)
            hours_diff = (dt - center_dt).total_seconds() / 3600  # Convert to hours
            
            # Scale to [-1, 1] where:
            # -1.0 = midnight UTC of center_date
            # 0.0 = noon UTC of center_date
            # +1.0 = midnight UTC of center_date + 1 day
            x = hours_diff / 24
        else:
            # Fallback to header's method if center_date not available
            x = self.header.datetime_to_hours(dt)
            
        return evaluate_chebyshev(self.coefficients, x)
