from datetime import datetime, timezone, date
from typing import Dict, List, Tuple, Optional, Union, cast
import time
from .weft_file import (
    WeftFile,
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    RangedBehavior,
    BlockType,
)


class WeftReader:
    """
    A reader for .weft files that handles value evaluation and interpolation.

    This class is responsible for:
    - Loading and managing a single .weft file
    - Evaluating values at specific times
    - Interpolating between 48-hour blocks in the same section
    - Handling value behaviors (wrapping, bounded, unbounded)

    Block priority for evaluation (highest to lowest):
    1. 48-hour blocks (with interpolation only between blocks in same section)
    2. Monthly blocks
    3. Multi-year blocks
    """

    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize a WeftReader.

        Args:
            file_path: Optional path to a .weft file to load
        """
        self.file: Optional[WeftFile] = None
        if file_path is not None:
            self.load_file(file_path)

    def load_file(self, file_path: str) -> WeftFile:
        """
        Load a .weft file.

        Args:
            file_path: Path to the .weft file

        Returns:
            The loaded WeftFile instance
        """
        start_time = time.time()
        with open(file_path, "rb") as f:
            data = f.read()
        read_time = time.time()

        self.file = WeftFile.from_bytes(data)
        parse_time = time.time()

        if self.file is not None:
            self.file.logger.info(
                f"File load timing: {read_time - start_time:.3f}s to read, "
                f"{parse_time - read_time:.3f}s to parse, "
                f"total {parse_time - start_time:.3f}s"
            )

        return self.file

    def get_info(self) -> dict[str, Union[str, list[BlockType], int]]:
        """
        Get information about the loaded .weft file.

        Returns:
            Dictionary containing file information

        Raises:
            ValueError: If no file is loaded
        """
        if self.file is None:
            raise ValueError("No file loaded")
        return self.file.get_info()

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """
        Get the date range covered by the loaded .weft file.

        Returns:
            Tuple of (start_date, end_date)

        Raises:
            ValueError: If no file is loaded or no blocks found
        """
        if self.file is None:
            raise ValueError("No file loaded")

        start_date = None
        end_date = None

        for block in self.file.blocks:
            if isinstance(block, MultiYearBlock):
                block_start = datetime(block.start_year, 1, 1, tzinfo=timezone.utc)
                block_end = datetime(
                    block.start_year + block.duration, 1, 1, tzinfo=timezone.utc
                )
            elif isinstance(block, MonthlyBlock):
                block_start = datetime(block.year, block.month, 1, tzinfo=timezone.utc)
                if block.month == 12:
                    block_end = datetime(block.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    block_end = datetime(
                        block.year, block.month + 1, 1, tzinfo=timezone.utc
                    )
            elif isinstance(block, FortyEightHourBlock):
                block_start = datetime.combine(
                    block.header.start_day, time(0, tzinfo=timezone.utc)
                )
                block_end = datetime.combine(
                    block.header.end_day, time(0, tzinfo=timezone.utc)
                )
            else:
                continue

            if start_date is None or block_start < start_date:
                start_date = block_start
            if end_date is None or block_end > end_date:
                end_date = block_end

        if start_date is None or end_date is None:
            raise ValueError("No blocks found in file")

        return start_date, end_date

    def get_value(self, dt: datetime) -> float:
        """
        Get a value from the loaded .weft file for a specific datetime.

        Args:
            dt: The datetime to get the value for (timezone-aware or naive)

        Returns:
            The value at the given datetime

        Raises:
            ValueError: If no file is loaded or no block covers the given time
        """
        if self.file is None:
            raise ValueError("No file loaded")

        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # Find all forty-eight hour blocks that contain this datetime
        forty_eight_hour_blocks = []
        for block in self.file.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                forty_eight_hour_blocks.append(block)

        # If we have forty-eight hour blocks, check if they're in the same section
        if forty_eight_hour_blocks:
            # Group blocks by their header
            blocks_by_header: Dict[Tuple[date, date], List[FortyEightHourBlock]] = {}
            for block in forty_eight_hour_blocks:
                header_key = (block.header.start_day, block.header.end_day)
                if header_key not in blocks_by_header:
                    blocks_by_header[header_key] = []
                blocks_by_header[header_key].append(block)

            # If we have multiple blocks in the same section, interpolate
            for blocks in blocks_by_header.values():
                if len(blocks) > 1:
                    self.file.logger.debug(
                        f"Interpolating between {len(blocks)} blocks in same section for {dt.isoformat()}"
                    )
                    return self._interpolate_blocks(blocks, dt)

            # Otherwise, just use the single block's value
            value = forty_eight_hour_blocks[0].evaluate(dt)
            self.file.logger.debug(
                f"Value {value} from FortyEightHourBlock for {dt.isoformat()}"
            )
            return self.apply_value_behavior(value)

        # Try monthly blocks next
        for block in self.file.blocks:
            if isinstance(block, MonthlyBlock) and block.contains(dt):
                value = block.evaluate(dt)
                self.file.logger.debug(
                    f"Value {value} from MonthlyBlock for {dt.isoformat()}"
                )
                return self.apply_value_behavior(value)

        # Finally, try multi-year blocks
        for block in self.file.blocks:
            if isinstance(block, MultiYearBlock) and block.contains(dt):
                value = block.evaluate(dt)
                self.file.logger.debug(
                    f"Value {value} from MultiYearBlock for {dt.isoformat()}"
                )
                return self.apply_value_behavior(value)

        raise ValueError(f"No block found for datetime: {dt}")

    def _interpolate_blocks(
        self, blocks: List[FortyEightHourBlock], dt: datetime
    ) -> float:
        """
        Interpolate between multiple blocks in the same section.

        Args:
            blocks: List of blocks to interpolate between
            dt: The datetime to evaluate at

        Returns:
            The interpolated value
        """
        # Sort blocks by date
        blocks = sorted(blocks, key=lambda b: b.header.start_day)

        # work in timestamp (floats) for easier calculation
        target_ts = dt.timestamp()

        weights = []
        for i, block in enumerate(blocks):
            # Calculate time distance from block's midpoint in hours
            time_diff = (
                abs(target_ts - block.midnight().timestamp()) / 3600
            )  # Convert to hours
            # Weight decreases linearly from 1 at midpoint to 0 at 24 hours away
            weight = max(0.0, 1.0 - time_diff / 24.0)
            weights.append(weight)

        # Log interpolation details
        if self.file is not None:
            self.file.logger.debug(
                f"Interpolating between {len(blocks)} blocks for {dt.isoformat()}"
            )
            for i, block in enumerate(blocks):
                self.file.logger.debug(
                    f"  Block {i + 1}: {block.midnight().isoformat()}, "
                    f"weight={weights[i]:.4f}, "
                    f"raw_value={block.evaluate(dt):.6f}"
                )

        # Normalize weights
        weight_sum = sum(weights)
        if weight_sum > 0:
            weights = [w / weight_sum for w in weights]
        else:
            # Fallback to using the closest block
            closest_block = min(
                blocks,
                key=lambda b: abs(dt.timestamp() - b.midnight().timestamp()),
            )
            return self.apply_value_behavior(closest_block.evaluate(dt))

        # Calculate values from each block
        block_values = [block.evaluate(dt) for block in blocks]

        # Handle wrapping angles
        if self._is_wrapping_angle():
            if self.file is None:
                raise ValueError("No file loaded")
            behavior = cast(RangedBehavior, self.file.value_behavior)
            min_val, max_val = behavior["range"]
            range_size = max_val - min_val

            # Normalize values
            normalized_values = [
                min_val + ((value - min_val) % range_size) for value in block_values
            ]

            # Check if crossing boundary
            crossing_boundary = False
            for i in range(len(normalized_values)):
                for j in range(i + 1, len(normalized_values)):
                    if (
                        abs(normalized_values[i] - normalized_values[j])
                        > range_size / 2
                    ):
                        crossing_boundary = True
                        break

            if crossing_boundary:
                # Unwrap values relative to first value
                reference = normalized_values[0]
                unwrapped_values = []
                for value in normalized_values:
                    diff = (
                        (value - reference + range_size / 2) % range_size
                    ) - range_size / 2
                    unwrapped_values.append(reference + diff)

                value = sum(v * w for v, w in zip(unwrapped_values, weights))
                result = min_val + ((value - min_val) % range_size)
            else:
                result = sum(v * w for v, w in zip(normalized_values, weights))
        else:
            value = sum(v * w for v, w in zip(block_values, weights))
            result = self.apply_value_behavior(value)

        if self.file is not None:
            self.file.logger.debug(
                f"Final interpolated value: {result:.6f} (weights: {', '.join(f'{w:.4f}' for w in weights)})"
            )

        return result

    def _is_wrapping_angle(self) -> bool:
        """
        Check if the file contains wrapping angle values.

        Returns:
            True if the file contains wrapping angle values
        """
        if self.file is None:
            raise ValueError("No file loaded")
        return self.file.value_behavior["type"] == "wrapping"

    def apply_value_behavior(self, value: float) -> float:
        """
        Apply value behavior to a value.

        Args:
            value: The value to process

        Returns:
            The processed value
        """
        if self.file is None:
            raise ValueError("No file loaded")

        behavior_type = self.file.value_behavior["type"]
        if behavior_type == "wrapping":
            min_val, max_val = cast(RangedBehavior, self.file.value_behavior)["range"]
            range_size = max_val - min_val
            while value < min_val:
                value += range_size
            while value >= max_val:
                value -= range_size
            return value
        elif behavior_type == "bounded":
            min_val, max_val = cast(RangedBehavior, self.file.value_behavior)["range"]
            return max(min_val, min(max_val, value))
        else:  # unbounded
            return value
