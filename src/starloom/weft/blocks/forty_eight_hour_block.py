"""
FortyEightHourBlock class for handling 48-hour periods with Chebyshev polynomials.
"""

import struct
from datetime import datetime, timezone
from typing import List, BinaryIO

from .forty_eight_hour_section_header import FortyEightHourSectionHeader
from .utils import evaluate_chebyshev


class FortyEightHourBlock:
    """A block containing coefficients for a 48-hour period."""

    marker = b"\x00\x01"  # Block type marker

    def __init__(self, header: FortyEightHourSectionHeader, coeffs: List[float]):
        """
        Initialize a forty-eight hour block.

        Args:
            header: The section header
            coeffs: Chebyshev polynomial coefficients

        Raises:
            ValueError: If any coefficient is NaN
        """
        self.header = header

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

        self.coeffs = coeffs

        # Pad to header's count for binary format
        self._full_coeffs = coeffs + [0.0] * (
            self.header.coefficient_count - len(coeffs)
        )

    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this block's range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within range
        """
        return self.header.contains_datetime(dt)

    def to_bytes(self) -> bytes:
        """
        Convert the block to binary format.

        Returns:
            Binary representation of block
        """
        # Convert coefficients to big-endian bytes
        coeffs_bytes = bytearray()
        for coeff in self._full_coeffs:
            coeffs_bytes.extend(struct.pack(">f", float(coeff)))
        return self.marker + bytes(coeffs_bytes)

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
        coeffs_bytes = stream.read(4 * header.coefficient_count)
        if len(coeffs_bytes) != 4 * header.coefficient_count:
            raise ValueError("Incomplete coefficient data")

        coeffs = []
        for i in range(0, len(coeffs_bytes), 4):
            coeff = struct.unpack(">f", coeffs_bytes[i : i + 4])[0]
            coeffs.append(coeff)

        return cls(header=header, coeffs=coeffs)

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

        dt = dt.astimezone(timezone.utc)
        x = self.header.datetime_to_hours(dt)
        return evaluate_chebyshev(self.coeffs, x)
