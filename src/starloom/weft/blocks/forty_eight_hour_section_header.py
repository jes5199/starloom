"""
FortyEightHourSectionHeader class for handling metadata for forty-eight hour blocks.
"""

import struct
from datetime import datetime, timezone, date
from typing import BinaryIO


class FortyEightHourSectionHeader:
    """A header that precedes forty-eight hour blocks.
    
    This header contains metadata about the time period covered by the following
    blocks. It is used to efficiently locate and validate blocks.
    """

    marker = b"\x00\x02"  # FortyEightHour section header marker
    coefficient_count = 48  # Number of coefficients in each block

    def __init__(
        self,
        start_day: date,
        end_day: date,
    ):
        """Initialize a FortyEightHour section header.

        Args:
            start_day: The start date of the section
            end_day: The end date of the section (exclusive)

        Raises:
            ValueError: If end_day is not after start_day
        """
        if end_day <= start_day:
            raise ValueError("End day must be after start day")
        self.start_day = start_day
        self.end_day = end_day

    def to_bytes(self) -> bytes:
        """Convert this header to bytes.

        Returns:
            The header as bytes
        """
        data = bytearray()
        data.extend(self.marker)
        # Write start date
        data.extend(struct.pack(">H", self.start_day.year))
        data.append(self.start_day.month)
        data.append(self.start_day.day)
        # Write end date
        data.extend(struct.pack(">H", self.end_day.year))
        data.append(self.end_day.month)
        data.append(self.end_day.day)
        return bytes(data)

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "FortyEightHourSectionHeader":
        """Read a header from a binary stream.

        Args:
            stream: The binary stream to read from

        Returns:
            A new FortyEightHourSectionHeader instance
        """
        # Read start date
        start_year = struct.unpack(">H", stream.read(2))[0]
        start_month = stream.read(1)[0]
        start_day = stream.read(1)[0]
        # Read end date
        end_year = struct.unpack(">H", stream.read(2))[0]
        end_month = stream.read(1)[0]
        end_day = stream.read(1)[0]
        return cls(
            start_day=date(start_year, start_month, start_day),
            end_day=date(end_year, end_month, end_day),
        )

    def contains_datetime(self, dt: datetime) -> bool:
        """Check if a datetime falls within this section's date range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime falls within this section's date range
        """
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_date = dt.date()
        return self.start_day <= dt_date < self.end_day

    def datetime_to_hours(self, dt: datetime) -> float:
        """Convert a datetime to normalized hours in [-1, 1].

        Args:
            dt: The datetime to convert

        Returns:
            The normalized hours value in [-1, 1]

        Raises:
            ValueError: If the datetime is outside this section's range
        """
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        if not self.contains_datetime(dt):
            raise ValueError("Datetime outside section range")
        # Convert to hours since start of day
        hours = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        # Normalize to [-1, 1]
        return 2.0 * (hours / 24.0) - 1.0 