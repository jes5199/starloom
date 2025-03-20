"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

import struct
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union, BinaryIO
import numpy as np
import re


def evaluate_chebyshev(coeffs: List[float], x: float) -> float:
    """
    Evaluate a Chebyshev polynomial at a specific point.

    Args:
        coeffs: List of Chebyshev coefficients
        x: Point to evaluate at (must be in range [-1, 1])

    Returns:
        The value of the polynomial at point x
    """
    if not -1 <= x <= 1:
        raise ValueError(f"x must be in range [-1, 1], got {x}")

    # Handle the base cases
    if len(coeffs) == 0:
        return 0.0
    if len(coeffs) == 1:
        return coeffs[0]

    # Use Clenshaw's recurrence formula for numerical stability
    b_k_plus_2 = 0.0
    b_k_plus_1 = 0.0

    # Start from the highest order term
    for k in range(len(coeffs) - 1, 0, -1):
        b_k = 2 * x * b_k_plus_1 - b_k_plus_2 + coeffs[k]
        b_k_plus_2 = b_k_plus_1
        b_k_plus_1 = b_k

    # Compute final result
    return x * b_k_plus_1 - b_k_plus_2 + coeffs[0]


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
        diff = ((angles[i] - unwrapped[i-1] + 180) % 360) - 180
        unwrapped.append(unwrapped[i-1] + diff)
    
    return unwrapped


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
        header = struct.pack(
            ">hhI", 
            self.start_year, 
            self.duration, 
            len(self.coeffs)
        )
        
        # Pack coefficients
        coeffs_bytes = struct.pack(">" + "f" * len(self.coeffs), *self.coeffs)
        
        return self.marker + header + coeffs_bytes
    
    @classmethod
    def from_stream(cls, stream: BinaryIO) -> 'MultiYearBlock':
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
        if not self.contains(dt):
            raise ValueError(f"Datetime {dt} is outside the block's range")
        
        # Convert datetime to normalized time in [-1, 1] range
        # x = -1 at start of period
        # x = 1 at end of period
        year_float = dt.year + (dt.timetuple().tm_yday - 1) / 366.0
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
            ">hBBI", 
            self.year, 
            self.month, 
            self.day_count, 
            len(self.coeffs)
        )
        
        # Pack coefficients
        coeffs_bytes = struct.pack(">" + "f" * len(self.coeffs), *self.coeffs)
        
        return self.marker + header + coeffs_bytes
    
    @classmethod
    def from_stream(cls, stream: BinaryIO) -> 'MonthlyBlock':
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
        return dt.year == self.year and dt.month == self.month
    
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
        if not self.contains(dt):
            raise ValueError(f"Datetime {dt} is outside the block's range")
        
        # Convert datetime to normalized time in [-1, 1] range
        # x = -1 at start of month
        # x = 1 at end of month
        start_of_month = datetime(self.year, self.month, 1, tzinfo=dt.tzinfo or timezone.utc)
        if self.month == 12:
            next_month = datetime(self.year + 1, 1, 1, tzinfo=dt.tzinfo or timezone.utc)
        else:
            next_month = datetime(self.year, self.month + 1, 1, tzinfo=dt.tzinfo or timezone.utc)
        
        total_seconds = (next_month - start_of_month).total_seconds()
        seconds_elapsed = (dt - start_of_month).total_seconds()
        x = 2 * (seconds_elapsed / total_seconds) - 1
        
        return evaluate_chebyshev(self.coeffs, x)


class DailySectionHeader:
    """
    Header for a section of daily blocks.
    
    This defines the date range and block size for subsequent DailyDataBlock instances.
    """
    
    marker = b"\x00\x02"  # Block type marker
    
    def __init__(
        self, 
        start_year: int, 
        start_month: int, 
        start_day: int,
        end_year: int, 
        end_month: int, 
        end_day: int,
        block_size: int, 
        block_count: int
    ):
        """
        Initialize a daily section header.
        
        Args:
            start_year: Start year
            start_month: Start month (1-12)
            start_day: Start day (1-31)
            end_year: End year
            end_month: End month (1-12)
            end_day: End day (1-31)
            block_size: Size in bytes of each daily block
            block_count: Number of daily blocks in this section
        """
        self.start_year = start_year
        self.start_month = start_month
        self.start_day = start_day
        self.end_year = end_year
        self.end_month = end_month
        self.end_day = end_day
        self.block_size = block_size
        self.block_count = block_count
    
    def to_bytes(self) -> bytes:
        """
        Convert the header to binary format.
        
        Returns:
            Binary representation of the header
        """
        # Format:
        # marker (2 bytes)
        # start_year (2 bytes, signed short)
        # start_month (1 byte, unsigned char)
        # start_day (1 byte, unsigned char)
        # end_year (2 bytes, signed short)
        # end_month (1 byte, unsigned char)
        # end_day (1 byte, unsigned char)
        # block_size (2 bytes, unsigned short)
        # block_count (4 bytes, unsigned int)
        header = struct.pack(
            ">hBBhBBHI", 
            self.start_year, 
            self.start_month, 
            self.start_day,
            self.end_year, 
            self.end_month, 
            self.end_day,
            self.block_size, 
            self.block_count
        )
        
        return self.marker + header
    
    @classmethod
    def from_stream(cls, stream: BinaryIO) -> 'DailySectionHeader':
        """
        Read a daily section header from a binary stream.
        
        Args:
            stream: Binary stream positioned after the marker
            
        Returns:
            A DailySectionHeader instance
        """
        # Read header
        header = stream.read(14)
        (
            start_year, 
            start_month, 
            start_day,
            end_year, 
            end_month, 
            end_day,
            block_size, 
            block_count
        ) = struct.unpack(">hBBhBBHI", header)
        
        return cls(
            start_year=start_year, 
            start_month=start_month, 
            start_day=start_day,
            end_year=end_year, 
            end_month=end_month, 
            end_day=end_day,
            block_size=block_size, 
            block_count=block_count
        )
    
    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this section's range.
        
        Args:
            dt: The datetime to check
            
        Returns:
            True if the datetime is within range
        """
        start_date = datetime(self.start_year, self.start_month, self.start_day)
        end_date = datetime(self.end_year, self.end_month, self.end_day) + timedelta(days=1)
        return start_date <= dt < end_date


class DailyDataBlock:
    """
    A block covering a single day with a Chebyshev polynomial.
    
    This provides high precision for fast-moving objects.
    """
    
    marker = b"\x00\x01"  # Block type marker
    
    def __init__(self, year: int, month: int, day: int, coeffs: List[float], block_size: int):
        """
        Initialize a daily data block.
        
        Args:
            year: Year
            month: Month (1-12)
            day: Day (1-31)
            coeffs: Chebyshev polynomial coefficients
            block_size: Total size of this block in bytes (including padding)
        """
        self.year = year
        self.month = month
        self.day = day
        self.coeffs = coeffs
        self.block_size = block_size
    
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
        # day (1 byte, unsigned char)
        # coefficients (4 bytes each, float)
        # padding (to reach block_size)
        header = struct.pack(
            ">hBB", 
            self.year, 
            self.month, 
            self.day
        )
        
        # Pack coefficients
        coeffs_bytes = struct.pack(">" + "f" * len(self.coeffs), *self.coeffs)
        
        # Calculate padding needed
        data = self.marker + header + coeffs_bytes
        padding_size = self.block_size - len(data)
        padding = bytes(padding_size) if padding_size > 0 else b""
        
        return data + padding
    
    @classmethod
    def from_stream(cls, stream: BinaryIO, block_size: int) -> 'DailyDataBlock':
        """
        Read a daily data block from a binary stream.
        
        Args:
            stream: Binary stream positioned after the marker
            block_size: Size of the block in bytes
            
        Returns:
            A DailyDataBlock instance
        """
        # Read header
        header = stream.read(4)
        year, month, day = struct.unpack(">hBB", header)
        
        # Calculate coefficient count based on block size
        # block_size = marker(2) + header(4) + coeffs(4*count) + padding
        # We've already read the marker and header, so:
        bytes_left = block_size - 6
        
        # Infer coefficient count assuming no padding
        # This is tricky since we don't know if there's padding
        # For now, assume all remaining bytes are coefficients
        coeff_count = bytes_left // 4
        
        # Read coefficients
        coeffs_bytes = stream.read(4 * coeff_count)
        coeffs = list(struct.unpack(">" + "f" * coeff_count, coeffs_bytes))
        
        # Skip padding if any
        padding_size = bytes_left - (4 * coeff_count)
        if padding_size > 0:
            stream.read(padding_size)
        
        return cls(year=year, month=month, day=day, coeffs=coeffs, block_size=block_size)
    
    def contains(self, dt: datetime) -> bool:
        """
        Check if a datetime is within this block's effective range.
        
        The effective range of a daily block is centered on the block's date and extends
        24 hours in each direction.
        
        Args:
            dt: The datetime to check
            
        Returns:
            True if the datetime is within range
        """
        # Get centered date for comparison
        block_date = datetime(self.year, self.month, self.day, 0, 0, 0, tzinfo=dt.tzinfo or timezone.utc)
        
        # Daily blocks cover a 48-hour window centered on midnight
        # i.e., from 24 hours before to 24 hours after midnight
        return block_date - timedelta(hours=24) <= dt < block_date + timedelta(hours=24)
    
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
        if not self.contains(dt):
            raise ValueError(f"Datetime {dt} is outside the block's range")
        
        # Convert datetime to normalized time in [-1, 1] range
        # x = -1 at midnight of the previous day
        # x = 0 at midnight of this day
        # x = 1 at midnight of the next day
        block_date = datetime(self.year, self.month, self.day, 0, 0, 0, tzinfo=dt.tzinfo or timezone.utc)
        
        # Calculate seconds from midnight of the previous day
        previous_day = block_date - timedelta(days=1)
        seconds_elapsed = (dt - previous_day).total_seconds()
        x = seconds_elapsed / 43200 - 1  # 43200 seconds = 12 hours
        
        return evaluate_chebyshev(self.coeffs, x)


class WeftFile:
    """
    A .weft binary ephemeris file.
    
    This represents a complete .weft file including preamble and multiple blocks.
    """
    
    def __init__(self, preamble: str, blocks: List[Any]):
        """
        Initialize a .weft file.
        
        Args:
            preamble: The UTF-8 preamble describing the file
            blocks: List of blocks (MultiYearBlock, MonthlyBlock, etc.)
        """
        self.preamble = preamble.rstrip("\n")
        self.blocks = blocks
        self.value_behavior = self._parse_value_behavior(preamble)
    
    def _parse_value_behavior(self, preamble: str) -> Dict[str, Any]:
        """
        Parse value behavior specifications from the preamble.
        
        Args:
            preamble: The file preamble
            
        Returns:
            Dictionary describing the value behavior
        """
        # Default behavior (unbounded)
        behavior = {
            "type": "unbounded"
        }
        
        # Check for wrapping behavior
        wrapping_match = re.search(r"wrapping\[([^,]+),([^]]+)\]", preamble)
        if wrapping_match:
            min_val = float(wrapping_match.group(1))
            max_val = float(wrapping_match.group(2))
            behavior = {
                "type": "wrapping",
                "range": (min_val, max_val)
            }
        
        # Check for bounded behavior
        bounded_match = re.search(r"bounded\[([^,]+),([^]]+)\]", preamble)
        if bounded_match:
            min_val = float(bounded_match.group(1))
            max_val = float(bounded_match.group(2))
            behavior = {
                "type": "bounded",
                "range": (min_val, max_val)
            }
        
        return behavior
    
    def apply_value_behavior(self, value: float) -> float:
        """
        Apply the file's value behavior to a computed value.
        
        Args:
            value: The raw value
            
        Returns:
            The value after applying wrapping/bounding
        """
        behavior_type = self.value_behavior.get("type", "unbounded")
        
        if behavior_type == "wrapping":
            min_val, max_val = self.value_behavior["range"]
            range_size = max_val - min_val
            return min_val + ((value - min_val) % range_size)
        
        elif behavior_type == "bounded":
            min_val, max_val = self.value_behavior["range"]
            return max(min_val, min(value, max_val))
        
        # Default: unbounded
        return value
    
    def to_bytes(self) -> bytes:
        """
        Convert the file to binary format.
        
        Returns:
            Binary representation of the file
        """
        # Start with preamble
        data = (self.preamble + "\n").encode("utf-8")
        
        # Add all blocks
        for block in self.blocks:
            data += block.to_bytes()
        
        return data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'WeftFile':
        """
        Parse a .weft file from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            A WeftFile instance
        """
        # Find the end of the preamble
        preamble_end = data.find(b"\n")
        if preamble_end == -1:
            raise ValueError("Invalid .weft file: no preamble terminator found")
        
        # Extract preamble
        preamble = data[:preamble_end].decode("utf-8")
        
        # Parse blocks
        blocks = []
        pos = preamble_end + 1
        
        # Keep track of current daily section header for block size
        current_daily_header = None
        
        while pos < len(data):
            # Read marker
            if pos + 2 > len(data):
                break
                
            marker = data[pos:pos+2]
            pos += 2
            
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
                
            elif marker == DailySectionHeader.marker:
                # Read daily section header
                stream = BytesIO(data[pos:])
                block = DailySectionHeader.from_stream(stream)
                blocks.append(block)
                pos += 14
                current_daily_header = block
                
            elif marker == DailyDataBlock.marker:
                # Read daily data block
                if current_daily_header is None:
                    raise ValueError("Daily data block found but no section header")
                    
                stream = BytesIO(data[pos:])
                block = DailyDataBlock.from_stream(stream, current_daily_header.block_size - 2)
                blocks.append(block)
                pos += current_daily_header.block_size - 2
                
            else:
                raise ValueError(f"Unknown block marker: {marker}")
        
        return cls(preamble=preamble, blocks=blocks)
    
    @classmethod
    def from_file(cls, filepath: str) -> 'WeftFile':
        """
        Read a .weft file from disk.
        
        Args:
            filepath: Path to the file
            
        Returns:
            A WeftFile instance
        """
        with open(filepath, "rb") as f:
            data = f.read()
        return cls.from_bytes(data)
    
    def write_to_file(self, filepath: str) -> None:
        """
        Write the .weft file to disk.
        
        Args:
            filepath: Path to write the file to
        """
        with open(filepath, "wb") as f:
            f.write(self.to_bytes()) 