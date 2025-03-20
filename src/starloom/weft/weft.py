"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

from datetime import datetime, timezone, time
from typing import Union, Tuple, Literal, TypedDict, Sequence
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
        value_behavior: Union[RangedBehavior, UnboundedBehavior] = UnboundedBehavior(
            type="unbounded"
        ),
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
        self, blocks: list[FortyEightHourBlock], dt: datetime
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

    def apply_value_behavior(self, value: float) -> float:
        """Apply value behavior rules to a value.

        Args:
            value: The value to process

        Returns:
            The processed value
        """
        if self.value_behavior["type"] == "wrapping":
            min_val, max_val = self.value_behavior["range"]
            range_size = max_val - min_val
            while value < min_val:
                value += range_size
            while value >= max_val:
                value -= range_size
            return value
        elif self.value_behavior["type"] == "bounded":
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
