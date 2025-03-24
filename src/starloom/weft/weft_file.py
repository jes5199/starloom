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
        # -- 1) Compare essential parts of the preambles to ensure compatibility
        parts1 = file1.preamble.strip().split()
        parts2 = file2.preamble.strip().split()

        # Both files must have at least 8 parts in the preamble
        if len(parts1) < 8 or len(parts2) < 8:
            raise ValueError("Invalid preamble format in one of the files")

        # Check planet, data source, precision, quantity, behavior, etc.
        # (Skipping timespan and generation timestamp in the comparison.)
        # Format reference for indexing:
        # 0: #weft!
        # 1: v0.02
        # 2: planet
        # 3: data_source
        # 4: timespan
        # 5: precision
        # 6: quantity
        # 7: behavior
        # 8: chebychevs
        # 9: generated@...
        def err(msg: str) -> None:
            raise ValueError(msg)

        if parts1[0] != parts2[0] or parts1[1] != parts2[1]:
            err("Weft format/version mismatch")
        if parts1[2] != parts2[2]:
            err(f"Files are for different planets: {parts1[2]} vs {parts2[2]}")
        if parts1[3] != parts2[3]:
            err(f"Different data sources: {parts1[3]} vs {parts2[3]}")
        if parts1[5] != parts2[5]:
            err(f"Files have different precision: {parts1[5]} vs {parts2[5]}")
        if parts1[6] != parts2[6]:
            err(f"Files contain different quantities: {parts1[6]} vs {parts2[6]}")
        if parts1[7] != parts2[7]:
            err(f"Files have different value behaviors: {parts1[7]} vs {parts2[7]}")

        # -- 2) Force load all 48-hour blocks in both files to ensure correct binary structure
        from .blocks.forty_eight_hour_section_header import FortyEightHourSectionHeader
        from .blocks.forty_eight_hour_block import FortyEightHourBlock
        from .blocks.monthly_block import MonthlyBlock
        from .blocks.multi_year_block import MultiYearBlock

        def force_load_48h_blocks(file: "WeftFile") -> list[BlockType]:
            """Force load all 48-hour blocks in a file."""
            new_blocks = []
            i = 0
            while i < len(file.blocks):
                block = file.blocks[i]
                if isinstance(block, FortyEightHourSectionHeader):
                    # For regular WeftFile, blocks are already loaded
                    if not hasattr(file, "get_blocks_in_section"):
                        # The next block.block_count blocks should be FortyEightHourBlocks
                        section_blocks = []
                        for _ in range(block.block_count):
                            i += 1
                            if i >= len(file.blocks):
                                raise ValueError(
                                    f"Section block count mismatch: expected {block.block_count} blocks, but reached end of file"
                                )
                            next_block = file.blocks[i]
                            if not isinstance(next_block, FortyEightHourBlock):
                                raise ValueError(
                                    f"Expected FortyEightHourBlock after header, got {type(next_block)}"
                                )
                            section_blocks.append(next_block)
                        new_blocks.append(block)
                        new_blocks.extend(section_blocks)
                    else:
                        # For LazyWeftFile, force load the blocks
                        section_blocks = file.get_blocks_in_section(block)
                        new_blocks.append(block)
                        new_blocks.extend(section_blocks)
                        i += block.block_count  # Skip the blocks we just loaded
                else:
                    new_blocks.append(block)
                i += 1
            return new_blocks

        # Force load blocks in both files
        file1.blocks = force_load_48h_blocks(file1)
        file2.blocks = force_load_48h_blocks(file2)

        # -- 3) Gather blocks from each file, separating 48-hour sections from the rest
        def is_48h_section(b) -> bool:
            return isinstance(b, (FortyEightHourSectionHeader, FortyEightHourBlock))

        def is_non_48h_block(b) -> bool:
            return isinstance(b, (MultiYearBlock, MonthlyBlock))

        # We keep track of each file's 48-hour sections as they appear
        # so we can re-inject them in chronological order as entire units.
        file1_sections: list[list] = []
        file2_sections: list[list] = []

        file1_non48 = []
        file2_non48 = []

        # Helper: walk a file's blocks, grouping each header plus its blocks
        # into a single sublist
        def split_sections(file_blocks):
            sections = []
            current_section = []
            for block in file_blocks:
                if isinstance(block, FortyEightHourSectionHeader):
                    # Once we hit a new header, push the old section if it has anything
                    if current_section:
                        sections.append(current_section)
                    current_section = [block]
                elif isinstance(block, FortyEightHourBlock):
                    # Belongs to the current header's section
                    if not current_section:
                        raise ValueError(
                            "Found a 48-hour block with no preceding header."
                        )
                    current_section.append(block)
                else:
                    # This is a non-48h block, not part of any section
                    if current_section:
                        sections.append(current_section)
                        current_section = []
                    # Return it as separate
                    yield None, block  # signal a non-48h block
            # End loop: if we had an open section, push it
            if current_section:
                sections.append(current_section)
            # Now yield all sections
            for sec in sections:
                yield sec, None

        # Fill file1_non48, file1_sections
        for sec, block in split_sections(file1.blocks):
            if sec is not None:
                file1_sections.append(sec)
            elif block is not None:
                file1_non48.append(block)

        # Fill file2_non48, file2_sections
        for sec, block in split_sections(file2.blocks):
            if sec is not None:
                file2_sections.append(sec)
            elif block is not None:
                file2_non48.append(block)

        # -- 4) Sort the non–48-hour blocks by date (multi-year or monthly) if desired
        def block_sort_key(b):
            if isinstance(b, MultiYearBlock):
                # Sort by (start_year, duration)
                return (b.start_year, b.duration)
            elif isinstance(b, MonthlyBlock):
                return (b.year, b.month)
            return (999999, 0)  # fallback

        file1_non48.sort(key=block_sort_key)
        file2_non48.sort(key=block_sort_key)

        # -- 5) Merge the two sets of non-48h blocks into a single sorted list
        merged_non48 = sorted(file1_non48 + file2_non48, key=block_sort_key)

        # -- 6) Construct the final block list
        final_blocks = []

        # First, collect all blocks by type
        multi_year_blocks = []
        monthly_blocks = []

        # Sort non-48h blocks by type and date
        for nb in merged_non48:
            if isinstance(nb, MultiYearBlock):
                multi_year_blocks.append(nb)
            elif isinstance(nb, MonthlyBlock):
                monthly_blocks.append(nb)

        # Sort multi-year blocks by start year and duration
        multi_year_blocks.sort(key=lambda b: (b.start_year, -b.duration))

        # Sort monthly blocks by date
        monthly_blocks.sort(key=lambda b: (b.year, b.month))

        # Add blocks in the correct order
        final_blocks.extend(multi_year_blocks)  # Multi-year blocks first
        final_blocks.extend(monthly_blocks)  # Then monthly blocks

        # Finally, add 48-hour sections in their original order from each file
        for sec in file1_sections:
            final_blocks.extend(sec)
        for sec in file2_sections:
            final_blocks.extend(sec)

        # -- 7) Build a new preamble with the updated timespan, newly generated@, etc.
        now = datetime.now(timezone.utc)
        # Keep everything from parts1 except we replace the timespan token with the user-provided timespan
        # parts1[4] is the old timespan
        new_preamble_parts = list(parts1)
        new_preamble_parts[4] = timespan  # replace with new combined timespan
        # Example new preamble:
        # #weft! v0.02 mercury jpl:xyz 1900s 32bit ecliptic_longitude wrapping[0,360] chebychevs generated@2025-03-24T...
        # We'll reassemble it carefully.
        new_preamble = (
            f"{new_preamble_parts[0]} {new_preamble_parts[1]} {new_preamble_parts[2]} "
            f"{new_preamble_parts[3]} {new_preamble_parts[4]} {new_preamble_parts[5]} "
            f"{new_preamble_parts[6]} {new_preamble_parts[7]} chebychevs "
            f"generated@{now.isoformat()}\n\n"
        )

        # -- 8) Return a new WeftFile with the combined blocks
        return cls(
            preamble=new_preamble,
            blocks=final_blocks,
            value_behavior=file1.value_behavior,  # same as file2 by previous checks
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
        section_positions: Optional[Dict[FortyEightHourSectionHeader, int]] = None,
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
                stream.seek(
                    current_header.block_size - 2, 1
                )  # -2 for the marker already read
            else:
                raise ValueError(f"Unknown block type marker: {marker!r}")

        # Return the LazyWeftFile with information needed for lazy loading
        return cls(
            preamble=preamble,
            blocks=blocks,
            file_data=data,
            section_positions=section_positions,
        )

    def get_blocks_in_section(
        self, header: FortyEightHourSectionHeader
    ) -> List[FortyEightHourBlock]:
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

    def get_forty_eight_hour_block_at_index(
        self, header: FortyEightHourSectionHeader, index: int
    ) -> FortyEightHourBlock:
        """
        Load a specific FortyEightHourBlock by its index in the section.

        Args:
            header: The section header
            index: The 0-based index of the block within the section

        Returns:
            The FortyEightHourBlock at the specified index

        Raises:
            ValueError: If the index is out of range or section cannot be loaded
        """
        if self.file_data is None or header not in self.section_positions:
            raise ValueError("Section not found or file data not available")

        if index < 0 or index >= header.block_count:
            raise ValueError(
                f"Block index {index} out of range (0-{header.block_count - 1})"
            )

        # Create stream from file data
        stream = BytesIO(self.file_data)

        # Calculate position of the specific block
        section_start = self.section_positions[header]
        block_position = section_start + (index * header.block_size)

        # Seek to the position of the block
        stream.seek(block_position)

        # Read the marker
        marker = stream.read(2)
        if marker != FortyEightHourBlock.marker:
            raise ValueError(
                f"Expected FortyEightHourBlock marker at index {index}, got {marker!r}"
            )

        # Read the block
        block = FortyEightHourBlock.from_stream(stream, header)
        return block

    def find_blocks_for_datetime_in_section(
        self, header: FortyEightHourSectionHeader, dt: datetime
    ) -> List[FortyEightHourBlock]:
        """
        Find FortyEightHourBlocks in a section that might contain the given datetime using binary search.

        Args:
            header: The section header
            dt: The datetime to find blocks for

        Returns:
            List of FortyEightHourBlocks that might contain the datetime

        Raises:
            ValueError: If the section cannot be loaded
        """
        if self.file_data is None or header not in self.section_positions:
            raise ValueError("Section not found or file data not available")

        if header.block_count == 0:
            return []

        # If there are only a few blocks, just load and check them all
        if header.block_count <= 5:
            blocks = []
            for i in range(header.block_count):
                block = self.get_forty_eight_hour_block_at_index(header, i)
                if block.contains(dt):
                    blocks.append(block)
            return blocks

        # Binary search to find potential blocks
        # Since 48-hour blocks have overlapping coverage (±24 hours),
        # we may need to check multiple blocks around our target
        low = 0
        high = header.block_count - 1
        target_date = dt.date()

        # First binary search to find a block closest to our target date
        while low <= high:
            mid = (low + high) // 2
            block = self.get_forty_eight_hour_block_at_index(header, mid)

            if block.center_date < target_date:
                low = mid + 1
            elif block.center_date > target_date:
                high = mid - 1
            else:
                # Exact match on date
                break

        # The loop exited, so mid is our best guess
        # Now check this block and potentially adjacent blocks
        potential_blocks = []

        # Get the range of blocks to check (at most 3 blocks)
        # This handles the 48-hour coverage overlap
        start_idx = max(0, mid - 1)
        end_idx = min(header.block_count - 1, mid + 1)

        # Check all potential blocks in range
        for i in range(start_idx, end_idx + 1):
            block = self.get_forty_eight_hour_block_at_index(header, i)
            if block.contains(dt):
                potential_blocks.append(block)

        return potential_blocks

    def get_forty_eight_hour_section_for_datetime(
        self, dt: datetime
    ) -> Optional[FortyEightHourSectionHeader]:
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
            if isinstance(
                block, FortyEightHourSectionHeader
            ) and block.contains_datetime(dt):
                return block

        return None

    def get_blocks_for_datetime(self, dt: datetime) -> List[BlockType]:
        """
        Get all blocks that contain the given datetime.
        Lazily loads FortyEightHourBlocks as needed, using binary search for efficiency.

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
            # Use binary search to find relevant blocks efficiently
            section_blocks = self.find_blocks_for_datetime_in_section(
                section_header, dt
            )
            result.extend(section_blocks)

        return result
