"""
FortyEightHourSectionHeader class for handling metadata for forty-eight hour blocks.
"""

import struct
from datetime import datetime, timezone, date, time
from typing import BinaryIO


class FortyEightHourSectionHeader:
    """Header for a forty-eight hour block."""

    marker = b"\x00\x02"  # Block type marker
    coefficient_count = 48  # Default number of coefficients

    def __init__(self, start_day: date, end_day: date, block_size: int, block_count: int):
        """Initialize a forty-eight hour section header.

        Args:
            start_day: Start date of the section
            end_day: End date of the section
            block_size: Size in bytes of each forty-eight hour block
            block_count: Number of forty-eight hour blocks in this section

        Raises:
            ValueError: If end_day is not after start_day
        """
        if not isinstance(start_day, date):
            raise ValueError("start_day must be a date object")
        if not isinstance(end_day, date):
            raise ValueError("end_day must be a date object")
        if end_day <= start_day:
            raise ValueError("end_day must be after start_day")
        if block_size < 0:
            raise ValueError("block_size must be non-negative")
        if block_count < 0:
            raise ValueError("block_count must be non-negative")

        self.start_day = start_day
        self.end_day = end_day
        self.block_size = block_size
        self.block_count = block_count

    def to_bytes(self) -> bytes:
        """Convert header to binary format.

        Returns:
            Binary representation of header
        """
        result = bytearray(self.marker)
        result.extend(struct.pack(">H", self.start_day.year))
        result.extend(struct.pack(">B", self.start_day.month))
        result.extend(struct.pack(">B", self.start_day.day))
        result.extend(struct.pack(">H", self.end_day.year))
        result.extend(struct.pack(">B", self.end_day.month))
        result.extend(struct.pack(">B", self.end_day.day))
        result.extend(struct.pack(">H", self.block_size))
        result.extend(struct.pack(">I", self.block_count))
        return bytes(result)

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "FortyEightHourSectionHeader":
        """Read header from binary stream.

        Args:
            stream: Binary stream to read from

        Returns:
            New FortyEightHourSectionHeader instance

        Raises:
            ValueError: If stream data is invalid
        """
        try:
            start_year = struct.unpack(">H", stream.read(2))[0]
            start_month = struct.unpack(">B", stream.read(1))[0]
            start_day = struct.unpack(">B", stream.read(1))[0]
            end_year = struct.unpack(">H", stream.read(2))[0]
            end_month = struct.unpack(">B", stream.read(1))[0]
            end_day = struct.unpack(">B", stream.read(1))[0]
            block_size = struct.unpack(">H", stream.read(2))[0]
            block_count = struct.unpack(">I", stream.read(4))[0]

            start = date(start_year, start_month, start_day)
            end = date(end_year, end_month, end_day)

            return cls(start_day=start, end_day=end, block_size=block_size, block_count=block_count)
        except (struct.error, ValueError) as e:
            raise ValueError(f"Invalid date data: {str(e)}")

    def contains_datetime(self, dt: datetime) -> bool:
        """Check if datetime falls within section's range.

        Args:
            dt: Datetime to check

        Returns:
            True if datetime is within range, False otherwise
        """
        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)

        dt_date = dt.date()
        return self.start_day <= dt_date < self.end_day

    def datetime_to_hours(self, dt: datetime) -> float:
        """Convert datetime to normalized hours in [-1, 1].

        Args:
            dt: Datetime to convert

        Returns:
            Normalized hours

        Raises:
            ValueError: If datetime is outside section range
        """
        if not self.contains_datetime(dt):
            raise ValueError("Datetime outside section range")

        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)

        # Calculate total seconds in the 48-hour period
        start_dt = datetime.combine(self.start_day, time(0, 0), timezone.utc)
        end_dt = datetime.combine(self.end_day, time(0, 0), timezone.utc)
        total_seconds = (end_dt - start_dt).total_seconds()

        # Calculate seconds elapsed since start
        elapsed = (dt - start_dt).total_seconds()

        # Convert to normalized hours in [-1, 1]
        return 2 * (elapsed / total_seconds) - 1
