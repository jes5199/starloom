"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

import struct
from datetime import datetime, timezone, timedelta, time, date
from typing import List, BinaryIO, Union, Tuple, Literal, Optional, TypedDict, cast
from io import BytesIO
import re
import math

# Define block types
BlockType = Union[
    "MultiYearBlock",
    "MonthlyBlock",
    "FortyEightHourSectionHeader",
    "FortyEightHourBlock",
]


# Define value behavior types
class RangedBehavior(TypedDict):
    type: Union[Literal["wrapping"], Literal["bounded"]]
    range: Tuple[float, float]


class UnboundedBehavior(TypedDict):
    type: Literal["unbounded"]


ValueBehavior = Union[RangedBehavior, UnboundedBehavior]


def evaluate_chebyshev(x: float, coeffs: List[float]) -> float:
    """
    Evaluate a Chebyshev polynomial at x using Clenshaw's algorithm.
    
    Args:
        x: Point at which to evaluate the polynomial (-1 <= x <= 1)
        coeffs: List of Chebyshev coefficients
        
    Returns:
        Value of the polynomial at x
        
    Raises:
        ValueError: If x is outside [-1, 1] or coeffs is empty
    """
    if not coeffs:
        raise ValueError("Must have at least one coefficient")
        
    if x < -1 or x > 1:
        raise ValueError("x must be in range [-1, 1]")
        
    # Special cases
    if len(coeffs) == 1:
        return coeffs[0]
        
    # Use Clenshaw's algorithm for numerical stability
    b_k1 = 0.0  # b_{k+1}
    b_k2 = 0.0  # b_{k+2}
    
    # Work backwards through coefficients
    for c in reversed(coeffs[1:]):
        b_k = c + 2 * x * b_k1 - b_k2
        b_k2 = b_k1
        b_k1 = b_k
        
    return coeffs[0] + x * b_k1 - b_k2


def unwrap_angles(angles: List[float]) -> List[float]:
    """
    Unwrap a sequence of angles to avoid jumps greater than 180 degrees.

    This is useful for angles like longitude which may wrap from 359 to 0.

    Args:
        angles: List of angles (in degrees)

    Returns:
        List of unwrapped angles
    """
    if not angles:
        return []

    # Make a copy to avoid modifying the original
    unwrapped = [angles[0]]

    for i in range(1, len(angles)):
        # Calculate the smallest angular difference
        diff = angles[i] - angles[i - 1]

        # Normalize to [-180, 180]
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        # Add the normalized difference to the previous unwrapped value
        unwrapped.append(unwrapped[i - 1] + diff)

    return unwrapped


def _ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime has timezone information, adding UTC if it doesn't.

    Args:
        dt: Datetime to check

    Returns:
        Timezone-aware datetime
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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

        return evaluate_chebyshev(x, self.coeffs)


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
            year: Year
            month: Month (1-12)
            day_count: Number of days in the month
            coeffs: Chebyshev polynomial coefficients
        """
        self.year = year
        self.month = month
        self.day_count = day_count
        self.coeffs = coeffs

    def to_bytes(self) -> bytes:
        """
        Convert the block to binary format.

        Returns:
            Binary representation of the block
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

        # Pack coefficients
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
        """
        # Read header
        header = stream.read(8)
        year, month, day_count, coeff_count = struct.unpack(">hBBI", header)

        # Read coefficients
        coeffs_bytes = stream.read(4 * coeff_count)
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
        dt = _ensure_timezone_aware(dt)

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
        dt = _ensure_timezone_aware(dt)

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

        return evaluate_chebyshev(x, self.coeffs)


class FortyEightHourSectionHeader:
    """Header for a 48-hour section containing multiple blocks."""

    marker = b"\x00\x02"
    coefficient_count = 6  # Number of coefficients per block

    def __init__(self, start_day: Union[date, datetime], end_day: Optional[Union[date, datetime]] = None):
        """
        Initialize a 48-hour section header.

        Args:
            start_day: Start date of the section (date or datetime)
            end_day: End date of the section (exclusive) (date or datetime)
                    If not provided, defaults to start_day + 1 day
        """
        # Convert datetime to date if needed
        if isinstance(start_day, datetime):
            start_day = start_day.date()

        if end_day is None:
            end_day = start_day + timedelta(days=1)
        elif isinstance(end_day, datetime):
            end_day = end_day.date()

        if end_day <= start_day:
            raise ValueError("end_day must be after start_day")

        if (end_day - start_day).days > 2:
            raise ValueError("Section cannot span more than 48 hours")

        self.start_day = start_day
        self.end_day = end_day

    @property
    def block_size(self) -> int:
        """Get the size of blocks in this section in bytes."""
        # 2 bytes for marker + 4 bytes per coefficient
        return 2 + (4 * self.coefficient_count)

    def to_bytes(self) -> bytes:
        """Convert the header to bytes."""
        # Write marker
        data = bytearray(self.marker)

        # Write start date
        data.extend(struct.pack(">H", self.start_day.year))
        data.extend(struct.pack(">B", self.start_day.month))
        data.extend(struct.pack(">B", self.start_day.day))

        # Write end date
        data.extend(struct.pack(">H", self.end_day.year))
        data.extend(struct.pack(">B", self.end_day.month))
        data.extend(struct.pack(">B", self.end_day.day))

        return bytes(data)

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "FortyEightHourSectionHeader":
        """Read a header from a binary stream."""
        # Read start date
        start_year = struct.unpack(">H", stream.read(2))[0]
        start_month = struct.unpack(">B", stream.read(1))[0]
        start_day = struct.unpack(">B", stream.read(1))[0]

        # Read end date
        end_year = struct.unpack(">H", stream.read(2))[0]
        end_month = struct.unpack(">B", stream.read(1))[0]
        end_day = struct.unpack(">B", stream.read(1))[0]

        # Create dates
        start_date = date(start_year, start_month, start_day)
        end_date = date(end_year, end_month, end_day)

        return cls(start_date, end_date)

    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this section's range.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within range
        """
        start_date = datetime(self.start_day.year, self.start_day.month, self.start_day.day)
        end_date = datetime(self.end_day.year, self.end_day.month, self.end_day.day) + timedelta(
            days=1
        )
        return start_date <= dt < end_date


class FortyEightHourBlock:
    """A block containing data for a 48-hour period."""

    marker = b"\x00\x01"

    def __init__(self, header: FortyEightHourSectionHeader, coefficients: List[float]):
        """
        Initialize a 48-hour block.

        Args:
            header: The section header this block belongs to
            coefficients: List of Chebyshev coefficients for interpolation.
                        When writing to disk, coefficients will be padded with zeros or
                        truncated to match the header's coefficient_count.

        Raises:
            ValueError: If any coefficient is NaN
        """
        if any(math.isnan(c) for c in coefficients):
            raise ValueError("Coefficients cannot be NaN")

        self.header = header
        self.coefficients = coefficients

    def to_bytes(self) -> bytes:
        """
        Convert the block to bytes.
        
        The coefficients will be padded with zeros or truncated to match
        the header's coefficient_count when writing to disk.
        """
        # Write marker
        data = bytearray(self.marker)

        # Get the target coefficient count from header
        target_count = self.header.coefficient_count
        
        # Pad or truncate coefficients to match header's count
        disk_coeffs = self.coefficients[:target_count]  # Truncate if too long
        if len(disk_coeffs) < target_count:
            # Pad with zeros if too short
            disk_coeffs.extend([0.0] * (target_count - len(disk_coeffs)))

        # Write coefficients
        for coeff in disk_coeffs:
            data.extend(struct.pack(">f", coeff))

        return bytes(data)

    @classmethod
    def from_stream(cls, stream: BinaryIO, header: FortyEightHourSectionHeader) -> "FortyEightHourBlock":
        """
        Read a block from a binary stream.
        
        Args:
            stream: Binary stream to read from
            header: The section header this block belongs to
            
        Returns:
            A new FortyEightHourBlock instance
        """
        # Read coefficients
        coeffs = []
        for _ in range(header.coefficient_count):
            coeff = struct.unpack(">f", stream.read(4))[0]
            coeffs.append(coeff)

        # Remove trailing zeros to preserve only meaningful coefficients
        while coeffs and coeffs[-1] == 0.0:
            coeffs.pop()

        return cls(header=header, coefficients=coeffs)

    def contains(self, dt: datetime) -> bool:
        """Check if this block contains the given datetime."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        start = datetime.combine(self.header.start_day, time(0), tzinfo=timezone.utc)
        end = datetime.combine(self.header.end_day, time(0), tzinfo=timezone.utc)

        return start <= dt < end

    def evaluate(self, dt: datetime) -> float:
        """
        Evaluate the block at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The interpolated value at the datetime

        Raises:
            ValueError: If the datetime is not within this block's range
        """
        if not self.contains(dt):
            raise ValueError("Datetime not within block range")

        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # Get start of block
        start = datetime.combine(self.header.start_day, time(0), tzinfo=timezone.utc)

        # Calculate normalized position in [-1, 1]
        hours = (dt - start).total_seconds() / 3600
        x = (hours / 48) * 2 - 1

        return evaluate_chebyshev(x, self.coefficients)


class WeftFile:
    """
    A .weft binary ephemeris file.

    This is the top-level container for ephemeris data.
    """

    def __init__(self, preamble: str, blocks: List[BlockType]):
        """
        Initialize a WeftFile.

        Args:
            preamble: File format preamble
            blocks: List of data blocks
        """
        if not preamble.startswith("#weft!"):
            raise ValueError("Invalid preamble")

        self.preamble = preamble
        self.blocks = blocks

    def to_bytes(self) -> bytes:
        """Convert the file to bytes."""
        # Write preamble
        data = bytearray(self.preamble.encode("utf-8"))

        # Write blocks
        for block in self.blocks:
            data.extend(block.to_bytes())

        return bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WeftFile":
        """Parse a .weft file from binary data."""
        # Find the end of the preamble (double newline)
        preamble_end = data.find(b"\n\n")
        if preamble_end == -1:
            raise ValueError("Invalid .weft file: no preamble terminator found")

        # Extract preamble
        preamble = data[:preamble_end + 1].decode("utf-8")

        # Parse blocks
        blocks: List[BlockType] = []
        pos = preamble_end + 2

        # Keep track of current daily section header for block size
        current_daily_header: Optional[FortyEightHourSectionHeader] = None

        while pos < len(data):
            # Read marker
            if pos + 2 > len(data):
                break

            marker = data[pos:pos + 2]
            pos += 2

            block: BlockType
            if marker == MultiYearBlock.marker:
                # Read multi-year block
                stream = BytesIO(data[pos:])
                block = MultiYearBlock.from_stream(stream)
                blocks.append(block)
                pos += 8 + 4 * len(block.coeffs)

            elif marker == MonthlyBlock.marker:
                # Read monthly block
                stream = BytesIO(data[pos:])
                block = MonthlyBlock.from_stream(stream)
                blocks.append(block)
                pos += 8 + 4 * len(block.coeffs)

            elif marker == FortyEightHourSectionHeader.marker:
                # Read forty-eight hour section header
                stream = BytesIO(data[pos:])
                block = FortyEightHourSectionHeader.from_stream(stream)
                blocks.append(block)
                pos += 8
                current_daily_header = block

            elif marker == FortyEightHourBlock.marker:
                # Read forty-eight hour block
                if current_daily_header is None:
                    raise ValueError(
                        "Forty-eight hour block found but no section header"
                    )

                stream = BytesIO(data[pos:])
                block = FortyEightHourBlock.from_stream(stream, current_daily_header)
                blocks.append(block)
                pos += 4 * 6  # 6 coefficients, 4 bytes each

            else:
                raise ValueError(f"Unknown block marker: {marker!r}")

        return cls(preamble, blocks)

    def evaluate(self, dt: datetime) -> float:
        """
        Evaluate the file at a specific datetime.

        Args:
            dt: The datetime to evaluate at

        Returns:
            The interpolated value at the datetime

        Raises:
            ValueError: If no block contains the datetime
        """
        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # Try daily blocks first (highest priority)
        daily_blocks = []
        for block in self.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                daily_blocks.append(block)

        # If we have daily blocks, use them
        if daily_blocks:
            # If multiple daily blocks cover this datetime, use linear interpolation
            if len(daily_blocks) > 1:
                return self._interpolate_daily_blocks(daily_blocks, dt)
            else:
                return daily_blocks[0].evaluate(dt)

        # Try monthly blocks next
        for block in self.blocks:
            if isinstance(block, MonthlyBlock) and block.contains(dt):
                return block.evaluate(dt)

        # Finally, try multi-year blocks
        for block in self.blocks:
            if isinstance(block, MultiYearBlock) and block.contains(dt):
                return block.evaluate(dt)

        raise ValueError(f"No block found for datetime: {dt}")

    def _interpolate_daily_blocks(
        self, blocks: List[FortyEightHourBlock], dt: datetime
    ) -> float:
        """
        Interpolate between overlapping daily blocks.

        Args:
            blocks: List of overlapping blocks
            dt: The datetime to evaluate at

        Returns:
            The interpolated value
        """
        # Get values and weights for each block
        values_and_weights = []
        for block in blocks:
            # Get block boundaries
            start = datetime.combine(
                block.header.start_day, time(0), tzinfo=timezone.utc
            )
            end = datetime.combine(
                block.header.end_day, time(0), tzinfo=timezone.utc
            )

            # Calculate weight based on position in block
            total_seconds = (end - start).total_seconds()
            seconds_from_start = (dt - start).total_seconds()
            weight = 1.0 - abs(seconds_from_start / total_seconds - 0.5) * 2

            # Evaluate block
            value = block.evaluate(dt)
            values_and_weights.append((value, weight))

        # Normalize weights
        total_weight = sum(w for _, w in values_and_weights)
        if total_weight == 0:
            # If all weights are 0, use simple average
            return sum(v for v, _ in values_and_weights) / len(values_and_weights)

        # Calculate weighted average
        weighted_sum = sum(v * w for v, w in values_and_weights)
        return weighted_sum / total_weight

    def write_to_file(self, filepath: str) -> None:
        """
        Write the .weft file to disk.

        Args:
            filepath: Path to write the file to
        """
        with open(filepath, "wb") as f:
            f.write(self.to_bytes())
