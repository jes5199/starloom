"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

from datetime import datetime, timezone, time
from typing import Union, Tuple, Literal, TypedDict, Sequence, List, Dict, Any
from io import BytesIO
from typing import cast

from .blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    FortyEightHourSectionHeader,
)
from .logging import get_logger

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
    """
    A .weft file containing ephemeris data.
    """

    def __init__(
        self,
        preamble: str,
        blocks: Sequence[BlockType],
        value_behavior: ValueBehavior = UnboundedBehavior(type="unbounded"),
    ):
        """
        Initialize a WeftFile.

        Args:
            preamble: The file preamble
            blocks: List of data blocks
            value_behavior: The value behavior (wrapping, bounded, or unbounded)
        """
        if not preamble.startswith("#weft!"):
            raise ValueError("Invalid preamble: must start with #weft!")

        # Ensure preamble ends with double newline
        if not preamble.endswith("\n\n"):
            preamble = preamble.rstrip("\n") + "\n\n"

        self.preamble = preamble
        self.blocks = list(blocks)
        self.value_behavior = value_behavior
        self.logger = get_logger(__name__)

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
        current_header: FortyEightHourSectionHeader = None
        current_header_blocks_read: int = 0
        
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
                # Check if we've read all the blocks for the previous header
                if current_header is not None and current_header_blocks_read != current_header.block_count:
                    raise ValueError(
                        f"Expected {current_header.block_count} FortyEightHourBlocks for header, but read {current_header_blocks_read}"
                    )
                    
                # Read the new header
                current_header = FortyEightHourSectionHeader.from_stream(stream)
                current_header_blocks_read = 0
                blocks.append(current_header)
            elif marker == FortyEightHourBlock.marker:
                if current_header is None:
                    raise ValueError("FortyEightHourBlock without a preceding header")
                
                # Read the block and validate it
                before_position = stream.tell()
                block = FortyEightHourBlock.from_stream(stream, current_header)
                after_position = stream.tell()
                
                # Check block size matches what's in the header
                actual_block_size = after_position - before_position + 2  # +2 for the marker
                if actual_block_size != current_header.block_size:
                    raise ValueError(
                        f"FortyEightHourBlock size mismatch: expected {current_header.block_size}, got {actual_block_size}"
                    )
                    
                blocks.append(block)
                current_header_blocks_read += 1
                
                # Check if we've reached the expected block count for this header
                if current_header_blocks_read == current_header.block_count:
                    # Reset for the next header
                    current_header = None
                    current_header_blocks_read = 0
            else:
                raise ValueError(f"Unknown block type marker: {marker!r}")

        # Final check for incomplete block set
        if current_header is not None and current_header_blocks_read != current_header.block_count:
            raise ValueError(
                f"Expected {current_header.block_count} FortyEightHourBlocks for final header, but read {current_header_blocks_read}"
            )

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
                self.logger.debug(
                    f"Using {len(forty_eight_hour_blocks)} FortyEightHourBlocks with interpolation for {dt.isoformat()}"
                )
                return self._interpolate_forty_eight_hour_blocks(
                    forty_eight_hour_blocks, dt
                )

            value = forty_eight_hour_blocks[0].evaluate(dt)
            block = forty_eight_hour_blocks[0]
            self.logger.debug(
                f"Value {value} from FortyEightHourBlock {block.month}: "
                f"{block.header.start_day.isoformat()} to {block.header.end_day.isoformat()} "
                f"for {dt.isoformat()}"
            )
            return value

        # Try monthly blocks next
        for block in self.blocks:
            if isinstance(block, MonthlyBlock) and block.contains(dt):
                value = block.evaluate(dt)
                self.logger.debug(
                    f"Value {value} from MonthlyBlock {id(block)}: "
                    f"year={block.year}, month={block.month} "
                    f"for {dt.isoformat()}"
                )
                return value

        # Finally, try multi-year blocks
        for block in self.blocks:
            if isinstance(block, MultiYearBlock) and block.contains(dt):
                value = block.evaluate(dt)
                self.logger.debug(
                    f"Value {value} from MultiYearBlock {id(block)}: "
                    f"start_year={block.start_year}, duration={block.duration} "
                    f"for {dt.isoformat()}"
                )
                return value

        raise ValueError(f"No block found for datetime: {dt}")

    def _interpolate_forty_eight_hour_blocks(
        self, blocks: List[FortyEightHourBlock], dt: datetime, debug: bool = False
    ) -> float:
        """
        Interpolate between multiple forty-eight hour blocks.

        When multiple forty-eight hour blocks cover the same datetime, we linearly
        interpolate between them based on their relative influence.

        Args:
            blocks: List of forty-eight hour blocks that contain the datetime
            dt: The datetime to evaluate at
            debug: If True, logs debug information about the interpolation

        Returns:
            The interpolated value
        """
        # Get values and weights for each block
        values_and_weights = []
        debug_blocks = []

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

            # Always collect debug info, logger will decide whether to use it
            debug_blocks.append(
                {
                    "id": id(block),
                    "start_day": block.header.start_day.isoformat(),
                    "end_day": block.header.end_day.isoformat(),
                    "weight": weight,
                    "value": value,
                }
            )

        # Normalize weights
        total_weight = sum(w for _, w in values_and_weights)
        if total_weight == 0:
            # If all weights are 0, use simple average
            value = sum(v for v, _ in values_and_weights) / len(values_and_weights)
            normalized_weights = [1.0 / len(blocks) for _ in blocks]
            self._log_interpolation_debug(
                debug_blocks, normalized_weights, value, "simple_average", dt
            )
            return value

        # Calculate weighted average
        weighted_sum = sum(v * w for v, w in values_and_weights)
        value = weighted_sum / total_weight

        normalized_weights = [w / total_weight for _, w in values_and_weights]
        self._log_interpolation_debug(
            debug_blocks, normalized_weights, value, "weighted_average", dt
        )

        return value

    def _log_interpolation_debug(
        self,
        blocks: List[Dict[str, Any]],
        normalized_weights: List[float],
        final_value: float,
        method: str,
        dt: datetime,
    ) -> None:
        """Log detailed interpolation debug information."""
        block_details = []
        for i, block in enumerate(blocks):
            block_details.append(
                f"Block {block['id']} ({block['start_day']} to {block['end_day']}): "
                f"value={block['value']}, weight={block['weight']:.4f}, "
                f"normalized_weight={normalized_weights[i]:.4f}"
            )

        self.logger.debug(
            f"Interpolated value {final_value} for {dt.isoformat()} using {method}:\n"
            f"  Total blocks: {len(blocks)}\n"
            f"  {chr(10)}  ".join(block_details)
        )

    def apply_value_behavior(self, value: float) -> float:
        """
        Apply value behavior to a value.

        Args:
            value: The value to process

        Returns:
            The processed value
        """
        behavior_type = self.value_behavior["type"]
        if behavior_type == "wrapping":
            min_val, max_val = cast(RangedBehavior, self.value_behavior)["range"]
            range_size = max_val - min_val
            while value < min_val:
                value += range_size
            while value >= max_val:
                value -= range_size
            return value
        elif behavior_type == "bounded":
            min_val, max_val = cast(RangedBehavior, self.value_behavior)["range"]
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
        """
        Combine two .weft files into a single file.

        Args:
            file1: The first .weft file
            file2: The second .weft file
            timespan: Descriptive timespan for the combined file

        Returns:
            A new WeftFile containing blocks from both files

        Raises:
            ValueError: If the files have incompatible preambles or block types
        """
        # Check that the preambles match (except for timespan and generated@)
        parts1 = file1.preamble.strip().split(" ")
        parts2 = file2.preamble.strip().split(" ")

        # Extract the fields we want to compare (skip timespan and generation timestamp)
        # Expected preamble format:
        # #weft! v0.02 planet data_source timespan precision quantity behavior chebychevs generated@timestamp
        if len(parts1) < 8 or len(parts2) < 8:
            raise ValueError("Invalid preamble format: too few parts")

        # Compare essential fields: format version, planet, data source, precision, quantity, behavior
        if (
            parts1[0:3] != parts2[0:3]  # #weft!, version, planet
            or parts1[3] != parts2[3]  # data_source
            or parts1[5] != parts2[5]  # precision
            or parts1[6] != parts2[6]  # quantity
            or parts1[7] != parts2[7]
        ):  # behavior
            # Provide more specific error message
            if parts1[2] != parts2[2]:
                raise ValueError(
                    f"Files are for different planets: {parts1[2]} vs {parts2[2]}"
                )
            elif parts1[3] != parts2[3]:
                raise ValueError(
                    f"Files use different data sources: {parts1[3]} vs {parts2[3]}"
                )
            elif parts1[5] != parts2[5]:
                raise ValueError(
                    f"Files have different precision specifications: {parts1[5]} vs {parts2[5]}"
                )
            elif parts1[6] != parts2[6]:
                raise ValueError(
                    f"Files contain different quantities: {parts1[6]} vs {parts2[6]}"
                )
            elif parts1[7] != parts2[7]:
                raise ValueError(
                    f"Files have different value behaviors: {parts1[7]} vs {parts2[7]}"
                )
            else:
                raise ValueError(
                    "Files have incompatible preambles and cannot be combined"
                )

        # Separate forty-eight hour blocks and their headers
        headers: List[FortyEightHourSectionHeader] = []
        header_to_blocks: Dict[FortyEightHourSectionHeader, List[FortyEightHourBlock]] = {}
        non_48h_blocks: List[Union[MultiYearBlock, MonthlyBlock]] = []

        # Define block sorting function
        def get_block_sort_key(
            block: Union[MultiYearBlock, MonthlyBlock],
        ) -> Tuple[int, int, datetime]:
            if isinstance(block, MultiYearBlock):
                # Use negative duration to sort longer periods first
                return (
                    0,
                    -block.duration,
                    datetime(block.start_year, 1, 1, tzinfo=timezone.utc),
                )
            else:  # Must be MonthlyBlock based on the type hint
                return (1, 0, datetime(block.year, block.month, 1, tzinfo=timezone.utc))

        for block in file1.blocks + file2.blocks:
            if isinstance(block, FortyEightHourSectionHeader):
                # Only add unique headers
                if block not in headers:
                    headers.append(block)
            elif isinstance(block, FortyEightHourBlock):
                header = block.header
                if header not in header_to_blocks:
                    header_to_blocks[header] = []
                header_to_blocks[header].append(block)
            elif isinstance(block, (MultiYearBlock, MonthlyBlock)):
                non_48h_blocks.append(block)

        # Sort headers by date
        headers.sort(key=lambda h: h.start_day)

        # Sort non-48h blocks by date
        non_48h_blocks.sort(key=get_block_sort_key)

        # Create the final block list
        final_blocks: List[BlockType] = []

        # First add all non-48h blocks
        for block in non_48h_blocks:
            final_blocks.append(block)

        # Then add headers and their blocks in chronological order
        for header in headers:
            if header not in header_to_blocks or not header_to_blocks[header]:
                raise ValueError(f"No 48-hour blocks found for header {header}")
                
            # Add header
            final_blocks.append(header)
            
            # Sort blocks by center date
            header_blocks = header_to_blocks[header]
            header_blocks.sort(key=lambda b: b.center_date)
            
            # Then add all blocks for this header
            final_blocks.extend(header_blocks)

        # Create new preamble
        now = datetime.now(timezone.utc)
        new_preamble = (
            f"{parts1[0]} {parts1[1]} {parts1[2]} {parts1[3]} {timespan} "
            f"{parts1[5]} {parts1[6]} {parts1[7]} chebychevs "
            f"generated@{now.isoformat()}\n\n"
        )

        # Create new file
        return cls(
            preamble=new_preamble,
            blocks=final_blocks,
            value_behavior=file1.value_behavior,
        )
