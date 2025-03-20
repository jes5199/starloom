"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

import struct
from datetime import datetime, timezone, time, date
from typing import List, BinaryIO, Union, Tuple, Literal, TypedDict
from io import BytesIO
import math
import numpy as np

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


def evaluate_chebyshev(coeffs: Union[List[float], np.ndarray], x: float) -> float:
    """Evaluate a Chebyshev polynomial at x using Clenshaw's algorithm.

    Args:
        coeffs: Chebyshev coefficients
        x: Point to evaluate at, must be in [-1, 1]

    Returns:
        Evaluated value

    Raises:
        ValueError: If x is outside [-1, 1]
    """
    if not -1 <= x <= 1:
        raise ValueError("x must be in [-1, 1]")

    # Convert coefficients to numpy array if needed
    if not isinstance(coeffs, np.ndarray):
        coeffs = np.array(coeffs, dtype=np.float32)

    # Handle empty or single coefficient case
    if len(coeffs) == 0:
        return 0.0
    if len(coeffs) == 1:
        return float(coeffs[0])

    # Clenshaw's algorithm
    b_k1 = 0.0  # b_{k+1}
    b_k2 = 0.0  # b_{k+2}
    x2 = 2.0 * x

    for c in coeffs[
        -1:0:-1
    ]:  # Iterate through coefficients in reverse, excluding first
        b_k = c + x2 * b_k1 - b_k2
        b_k2 = b_k1
        b_k1 = b_k

    return float(coeffs[0] + x * b_k1 - b_k2)


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

    Raises:
        ValueError: If the datetime is naive (no timezone)
    """
    if dt.tzinfo is None:
        raise ValueError("Datetime must have timezone information")
    return dt.astimezone(timezone.utc)


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

        return evaluate_chebyshev(self.coeffs, x)


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

        return evaluate_chebyshev(self.coeffs, x)


class FortyEightHourSectionHeader:
    """Header for a forty-eight hour block."""

    marker = b"\x00\x02"
    coefficient_count = 48  # Default number of coefficients

    def __init__(self, start_day: date, end_day: date):
        """Initialize a forty-eight hour section header.

        Args:
            start_day: Start date of the section
            end_day: End date of the section

        Raises:
            ValueError: If end_day is not after start_day
        """
        if not isinstance(start_day, date):
            raise ValueError("start_day must be a date object")
        if not isinstance(end_day, date):
            raise ValueError("end_day must be a date object")
        if end_day <= start_day:
            raise ValueError("end_day must be after start_day")

        self.start_day = start_day
        self.end_day = end_day

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

            start = date(start_year, start_month, start_day)
            end = date(end_year, end_month, end_day)

            return cls(start_day=start, end_day=end)
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


class FortyEightHourBlock:
    """A block containing coefficients for a 48-hour period."""

    marker = b"\x00\x01"

    def __init__(self, header: FortyEightHourSectionHeader, coeffs: List[float]):
        """
        Initialize a forty-eight hour block.

        Args:
            header: The section header
            coeffs: Chebyshev polynomial coefficients

        Raises:
            ValueError: If coefficients length doesn't match header's count or if any coefficient is NaN
        """
        self.header = header

        # Validate minimum coefficient count
        if len(coeffs) < 3:
            raise ValueError("At least 3 coefficients are required")

        # Check for NaN values
        if any(math.isnan(c) for c in coeffs):
            raise ValueError("Coefficients cannot contain NaN values")

        # Convert to numpy array for efficient operations
        coeffs_array = np.array(coeffs, dtype=np.float32)

        # Find last non-zero coefficient
        last_nonzero = -1
        for i in range(len(coeffs_array) - 1, -1, -1):
            if abs(coeffs_array[i]) > 1e-10:  # Use small epsilon for float comparison
                last_nonzero = i
                break

        # Keep only significant coefficients
        self.coeffs = coeffs_array[: last_nonzero + 1]

        # If all coefficients are effectively zero, keep just the first one
        if len(self.coeffs) == 0:
            self.coeffs = coeffs_array[:1]

        # Pad to header's count for binary format
        self._full_coeffs = np.pad(
            self.coeffs, (0, self.header.coefficient_count - len(self.coeffs))
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


class WeftFile:
    """A .weft file containing multiple blocks of data."""

    def __init__(self, preamble: str, blocks: List[BlockType]):
        """Initialize a .weft file.

        Args:
            preamble: File format preamble
            blocks: List of blocks in the file

        Raises:
            ValueError: If preamble is invalid
        """
        if not preamble.startswith("#weft!"):
            raise ValueError("Invalid preamble: must start with #weft!")

        # Ensure preamble ends with double newline
        if not preamble.endswith("\n\n"):
            preamble = preamble.rstrip("\n") + "\n\n"

        self.preamble = preamble
        self.blocks = blocks

    def get_info(self) -> dict:
        """Get information about the file.

        Returns:
            Dictionary containing file information
        """
        return {
            "preamble": self.preamble,
            "blocks": self.blocks,
            "block_count": len(self.blocks),
        }

    def to_bytes(self) -> bytes:
        """Convert file to binary format.

        Returns:
            Binary representation of file
        """
        result = bytearray(self.preamble.encode("utf-8"))
        for block in self.blocks:
            result.extend(block.to_bytes())
        return bytes(result)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WeftFile":
        """
        Create a WeftFile from binary data.

        Args:
            data: Binary data to read from

        Returns:
            A WeftFile instance

        Raises:
            ValueError: If the data format is invalid
        """
        # Read preamble
        stream = BytesIO(data)
        preamble = ""
        while True:
            char = stream.read(1).decode("utf-8")
            preamble += char
            if preamble.endswith("\n\n"):
                break
            if len(preamble) > 1000:  # Reasonable maximum preamble size
                raise ValueError("Invalid preamble format")

        blocks = []
        while True:
            # Try to read marker
            marker = stream.read(2)
            if not marker:  # End of file
                break

            # Determine block type and read
            if marker == MultiYearBlock.marker:
                blocks.append(MultiYearBlock.from_stream(stream))
            elif marker == MonthlyBlock.marker:
                blocks.append(MonthlyBlock.from_stream(stream))
            elif marker == FortyEightHourSectionHeader.marker:
                blocks.append(FortyEightHourSectionHeader.from_stream(stream))
            elif marker == FortyEightHourBlock.marker:
                if not blocks or not isinstance(
                    blocks[-1], FortyEightHourSectionHeader
                ):
                    raise ValueError("FortyEightHourBlock without preceding header")
                blocks.append(FortyEightHourBlock.from_stream(stream, blocks[-1]))
            else:
                raise ValueError(f"Unknown block type marker: {marker}")

        return cls(preamble=preamble, blocks=blocks)

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
            end = datetime.combine(block.header.end_day, time(0), tzinfo=timezone.utc)

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
