"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

from datetime import datetime, timezone, time
from typing import Union, Tuple, Literal, TypedDict, Sequence, List
from io import BytesIO

from .blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    FortyEightHourSectionHeader,
)

__all__ = [
    "WeftFile",
    "BlockType",
    "RangedBehavior",
    "UnboundedBehavior",
    "MultiYearBlock",
    "MonthlyBlock",
    "FortyEightHourBlock",
    "FortyEightHourSectionHeader",
]

# Define block types
BlockType = Union[
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
]


# Define value behavior types
class RangedBehavior(TypedDict):
    type: Union[Literal["wrapping"], Literal["bounded"]]
    range: Tuple[float, float]


class UnboundedBehavior(TypedDict):
    type: Literal["unbounded"]


ValueBehavior = Union[RangedBehavior, UnboundedBehavior]


class WeftFile:
    """A .weft file containing multiple blocks of data."""

    def __init__(
        self,
        preamble: str,
        blocks: Sequence[BlockType],
        value_behavior: ValueBehavior = UnboundedBehavior(type="unbounded"),
    ):
        """Initialize a .weft file.

        Args:
            preamble: File format preamble
            blocks: List of blocks in the file
            value_behavior: How to handle values during interpolation

        Raises:
            ValueError: If preamble is invalid
        """
        if not preamble.startswith("#weft!"):
            raise ValueError("Invalid preamble: must start with #weft!")

        # Ensure preamble ends with double newline
        if not preamble.endswith("\n\n"):
            preamble = preamble.rstrip("\n") + "\n\n"

        self.preamble = preamble
        self.blocks = list(blocks)  # Convert to list for internal storage
        self.value_behavior = value_behavior

    def get_info(self) -> dict[str, Union[str, list[BlockType], int]]:
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

        blocks: list[BlockType] = []
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
                raise ValueError(f"Unknown block type marker: {marker!r}")

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

        # Find all forty-eight hour blocks that contain this datetime
        forty_eight_hour_blocks = []
        for block in self.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                forty_eight_hour_blocks.append(block)

        # If we have forty-eight hour blocks, use them with interpolation
        if forty_eight_hour_blocks:
            if len(forty_eight_hour_blocks) > 1:
                return self._interpolate_forty_eight_hour_blocks(
                    forty_eight_hour_blocks, dt
                )
            return forty_eight_hour_blocks[0].evaluate(dt)

        # Try monthly blocks next
        for block in self.blocks:
            if isinstance(block, MonthlyBlock) and block.contains(dt):
                return block.evaluate(dt)

        # Finally, try multi-year blocks
        for block in self.blocks:
            if isinstance(block, MultiYearBlock) and block.contains(dt):
                return block.evaluate(dt)

        raise ValueError(f"No block found for datetime: {dt}")

    def _interpolate_forty_eight_hour_blocks(
        self, blocks: List[FortyEightHourBlock], dt: datetime
    ) -> float:
        """
        Interpolate between multiple forty-eight hour blocks.

        When multiple forty-eight hour blocks cover the same datetime, we linearly
        interpolate between them based on their relative influence.

        Args:
            blocks: List of forty-eight hour blocks that contain the datetime
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

    def apply_value_behavior(self, value: float) -> float:
        """Apply value behavior rules to a value.

        Args:
            value: The value to process

        Returns:
            The processed value
        """
        behavior_type = self.value_behavior["type"]
        if behavior_type == "wrapping":
            min_val, max_val = self.value_behavior["range"]
            range_size = max_val - min_val
            while value < min_val:
                value += range_size
            while value >= max_val:
                value -= range_size
            return value
        elif behavior_type == "bounded":
            min_val, max_val = self.value_behavior["range"]
            return max(min_val, min(max_val, value))
        else:  # unbounded
            return value

    def write_to_file(self, filepath: str) -> None:
        """
        Write the .weft file to disk.

        Args:
            filepath: Path to write the file to
        """
        with open(filepath, "wb") as f:
            f.write(self.to_bytes())

    @classmethod
    def combine(
        cls,
        file1: "WeftFile",
        file2: "WeftFile",
        timespan: str,
    ) -> "WeftFile":
        """Combine two .weft files into a single file.

        Args:
            file1: First .weft file
            file2: Second .weft file
            timespan: Descriptive timespan string (e.g. '2024s' or '2024-2025')

        Returns:
            A new WeftFile containing the combined data

        Raises:
            ValueError: If the files have incompatible preambles
        """
        # Compare preambles (ignoring timespan and generation timestamp)
        preamble1 = file1.preamble.strip()
        preamble2 = file2.preamble.strip()

        # Split preambles into components
        parts1 = preamble1.split()
        parts2 = preamble2.split()

        # Compare relevant parts (version, planet, source, precision, quantity, behavior)
        if parts1[0:2] != parts2[0:2]:  # version
            raise ValueError("Files have different versions")
        if parts1[2] != parts2[2]:  # planet
            raise ValueError("Files are for different planets")
        if parts1[3] != parts2[3]:  # source
            raise ValueError("Files use different data sources")
        if parts1[4] != parts2[4]:  # precision
            raise ValueError("Files have different precision")
        if parts1[5] != parts2[5]:  # quantity
            raise ValueError("Files contain different quantities")
        if parts1[6] != parts2[6]:  # behavior
            raise ValueError("Files have different value behaviors")

        # Merge blocks
        all_blocks = file1.blocks + file2.blocks

        # Sort blocks in the same order as WeftWriter:
        # 1. Multi-year blocks (decades first, then years)
        # 2. Monthly blocks
        # 3. Forty-eight hour section header followed by its blocks
        def get_block_sort_key(block: BlockType) -> Tuple[int, datetime]:
            if isinstance(block, MultiYearBlock):
                # Decades come before years
                is_decade = block.duration >= 10
                return (0, datetime(block.start_year, 1, 1, tzinfo=timezone.utc))
            elif isinstance(block, MonthlyBlock):
                return (1, datetime(block.year, block.month, 1, tzinfo=timezone.utc))
            elif isinstance(block, FortyEightHourSectionHeader):
                return (2, datetime.combine(block.start_day, time(0), tzinfo=timezone.utc))
            elif isinstance(block, FortyEightHourBlock):
                # Keep 48-hour blocks with their headers
                return (2, datetime.combine(block.header.start_day, time(0), tzinfo=timezone.utc))
            else:
                return (3, datetime.min.replace(tzinfo=timezone.utc))

        # Sort blocks
        all_blocks.sort(key=get_block_sort_key)

        # Create new preamble
        now = datetime.utcnow()
        new_preamble = (
            f"#weft! v0.02 {parts1[2]} {parts1[3]} {timespan} "
            f"{parts1[4]} {parts1[5]} {parts1[6]} chebychevs "
            f"generated@{now.isoformat()}\n\n"
        )

        # Create new file
        return cls(
            preamble=new_preamble,
            blocks=all_blocks,
            value_behavior=file1.value_behavior,
        )
