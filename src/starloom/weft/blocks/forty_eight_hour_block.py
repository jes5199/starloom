"""
FortyEightHourBlock class for handling 48-hour periods with Chebyshev polynomials.
"""

import struct
from datetime import datetime, timezone
from typing import List, BinaryIO
import numpy as np

from .forty_eight_hour_section_header import FortyEightHourSectionHeader
from .utils import evaluate_chebyshev


class FortyEightHourBlock:
    """A block that covers a 48-hour period with a Chebyshev polynomial.
    
    This block type provides high precision but uses more space than monthly blocks.
    It is typically used for fast-moving objects like the Moon or for high-precision
    applications.
    """

    marker = b"\x00\x03"  # FortyEightHour block marker

    def __init__(
        self,
        header: FortyEightHourSectionHeader,
        coeffs: List[float],
    ):
        """Initialize a FortyEightHour block.

        Args:
            header: The section header containing the date range
            coeffs: List of Chebyshev polynomial coefficients
        """
        self.header = header
        if any(np.isnan(c) for c in coeffs):
            raise ValueError("Coefficients cannot be NaN")
        # Store coefficients, stripping trailing zeros
        self.coeffs = coeffs
        # Store full coefficients for binary format
        self._full_coeffs = np.array(coeffs + [0.0] * (
            self.header.coefficient_count - len(coeffs)
        ))

    def contains(self, dt: datetime) -> bool:
        """Check if a datetime falls within this block's range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime falls within this block's range
        """
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return self.header.contains_datetime(dt)

    def to_bytes(self) -> bytes:
        """Convert this block to bytes.

        Returns:
            The block as bytes
        """
        data = bytearray()
        data.extend(self.marker)
        # Write coefficients
        for coeff in self._full_coeffs:
            data.extend(struct.pack(">f", coeff))
        return bytes(data)

    @classmethod
    def from_stream(
        cls, stream: BinaryIO, header: FortyEightHourSectionHeader
    ) -> "FortyEightHourBlock":
        """Read a block from a binary stream.

        Args:
            stream: The binary stream to read from
            header: The section header containing the date range

        Returns:
            A new FortyEightHourBlock instance
        """
        # Read coefficients
        coeffs = []
        for _ in range(header.coefficient_count):
            coeff = struct.unpack(">f", stream.read(4))[0]
            coeffs.append(coeff)
        # Strip trailing zeros
        while coeffs and coeffs[-1] == 0.0:
            coeffs.pop()
        if not coeffs:
            coeffs = [0.0]
        return cls(header=header, coeffs=coeffs)

    def evaluate(self, dt: datetime) -> float:
        """Evaluate the polynomial at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The value of the polynomial at the given datetime

        Raises:
            ValueError: If the datetime is outside this block's range
        """
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        if not self.contains(dt):
            raise ValueError("Datetime outside block range")
        x = self.header.datetime_to_hours(dt)
        return evaluate_chebyshev(self.coeffs, x) 