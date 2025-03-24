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
    "LazyWeftFile",
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

class LazyWeftFile(WeftFile):
    """
    A WeftFile implementation that lazily loads FortyEightHourBlocks.
    
    This implementation improves performance by:
    1. Reading and parsing MultiYearBlocks and MonthlyBlocks immediately
    2. Reading FortyEightHourSectionHeaders immediately
    3. Deferring reading of FortyEightHourBlocks until they are needed
    
    When a FortyEightHourBlock is requested, it will be loaded from the original file data
    based on its section header information.
    """
    
    def __init__(
        self,
        preamble: str,
        blocks: Sequence[BlockType],
        value_behavior: ValueBehavior = UnboundedBehavior(type="unbounded"),
        file_data: Optional[bytes] = None,
        section_positions: Optional[Dict[FortyEightHourSectionHeader, int]] = None
    ):
        """
        Initialize a LazyWeftFile.
        
        Args:
            preamble: The file preamble
            blocks: List of data blocks (excluding FortyEightHourBlocks)
            value_behavior: The value behavior
            file_data: Original binary file data
            section_positions: Dict mapping section headers to file positions
        """
        super().__init__(preamble, blocks, value_behavior)
        self.file_data = file_data
        self.section_positions = section_positions or {}
        
    @classmethod
    def from_bytes(cls, data: bytes) -> "LazyWeftFile":
        """
        Create a LazyWeftFile from binary data.
        
        Args:
            data: Binary data to read from
            
        Returns:
            A LazyWeftFile instance with lazily loaded FortyEightHourBlocks
            
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
        section_positions: Dict[FortyEightHourSectionHeader, int] = {}
        
        while True:
            # Save current position before marker
            marker_position = stream.tell()
            
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
                # Read the new header
                header = FortyEightHourSectionHeader.from_stream(stream)
                blocks.append(header)
                
                # Store the position right after the header
                section_positions[header] = stream.tell()
                current_header = header
                
                # Skip all the blocks in this section instead of reading them
                section_size = header.block_size * header.block_count
                stream.seek(section_size, 1)  # Seek relative to current position
            elif marker == FortyEightHourBlock.marker:
                # We shouldn't reach here with lazy loading, but if we do:
                if current_header is None:
                    raise ValueError("FortyEightHourBlock without a preceding header")
                    
                # Skip the block
                stream.seek(current_header.block_size - 2, 1)  # -2 for the marker already read
            else:
                raise ValueError(f"Unknown block type marker: {marker!r}")
                
        # Return the LazyWeftFile with information needed for lazy loading
        return cls(
            preamble=preamble,
            blocks=blocks,
            file_data=data,
            section_positions=section_positions
        )
        
    def get_blocks_in_section(self, header: FortyEightHourSectionHeader) -> List[FortyEightHourBlock]:
        """
        Load FortyEightHourBlocks for a specific section header.
        
        Args:
            header: The section header to load blocks for
            
        Returns:
            List of FortyEightHourBlocks in the section
            
        Raises:
            ValueError: If the section cannot be loaded
        """
        if self.file_data is None or header not in self.section_positions:
            raise ValueError("Section not found or file data not available")
            
        # Create stream from file data
        stream = BytesIO(self.file_data)
        
        # Seek to the position right after the header
        stream.seek(self.section_positions[header])
        
        # Read all blocks in this section
        blocks = []
        for _ in range(header.block_count):
            marker = stream.read(2)
            if marker != FortyEightHourBlock.marker:
                raise ValueError(f"Expected FortyEightHourBlock marker, got {marker!r}")
                
            block = FortyEightHourBlock.from_stream(stream, header)
            blocks.append(block)
            
        return blocks
        
    def get_forty_eight_hour_section_for_datetime(self, dt: datetime) -> Optional[FortyEightHourSectionHeader]:
        """
        Find the FortyEightHourSectionHeader containing the given datetime.
        
        Args:
            dt: The datetime to find a section for
            
        Returns:
            FortyEightHourSectionHeader if found, None otherwise
        """
        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
            
        # Find section header containing the datetime
        for block in self.blocks:
            if isinstance(block, FortyEightHourSectionHeader) and block.contains_datetime(dt):
                return block
                
        return None
        
    def get_blocks_for_datetime(self, dt: datetime) -> List[BlockType]:
        """
        Get all blocks that contain the given datetime.
        Lazily loads FortyEightHourBlocks as needed.
        
        Args:
            dt: The datetime to get blocks for
            
        Returns:
            List of blocks containing the datetime
        """
        result = []
        
        # Check all loaded blocks first
        for block in self.blocks:
            if isinstance(block, (MultiYearBlock, MonthlyBlock)) and block.contains(dt):
                result.append(block)
        
        # Check for and load forty-eight hour blocks
        section_header = self.get_forty_eight_hour_section_for_datetime(dt)
        if section_header is not None:
            # Lazy-load 48-hour blocks for this section
            section_blocks = self.get_blocks_in_section(section_header)
            
            # Add only those that contain the datetime
            for section_block in section_blocks:
                if section_block.contains(dt):
                    result.append(section_block)
                    
        return result
