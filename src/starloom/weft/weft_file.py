"""
Weft binary ephemeris format implementation.

The .weft format is a compact binary ephemeris format using Chebyshev polynomials
to store astronomical values efficiently. It supports multiple levels of precision:
- Multi-year blocks for long-term, low-precision data
- Monthly blocks for medium-term, medium-precision data
- Daily blocks for short-term, high-precision data
"""

from datetime import datetime, timezone
from typing import Union, Tuple, Literal, TypedDict, Sequence, List, Dict, Optional
from io import BytesIO

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

    This class handles the low-level aspects of .weft files:
    - File structure and format
    - Binary serialization/deserialization
    - Block storage and management
    - File I/O operations

    It does not handle value evaluation or interpolation - those responsibilities
    belong to WeftReader.
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
        current_header: Optional[FortyEightHourSectionHeader] = None
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
                if (
                    current_header is not None
                    and current_header_blocks_read != current_header.block_count
                ):
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
                actual_block_size = (
                    after_position - before_position + 2
                )  # +2 for the marker
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
        if (
            current_header is not None
            and current_header_blocks_read != current_header.block_count
        ):
            raise ValueError(
                f"Expected {current_header.block_count} FortyEightHourBlocks for final header, but read {current_header_blocks_read}"
            )

        return cls(preamble=preamble, blocks=blocks)

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
        header_to_blocks: Dict[
            FortyEightHourSectionHeader, List[FortyEightHourBlock]
        ] = {}
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
