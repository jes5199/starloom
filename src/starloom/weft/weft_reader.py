from datetime import datetime, timezone, time
from typing import Dict, List, Tuple, Optional, Union, cast
from .weft import (
    WeftFile,
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    RangedBehavior,
    BlockType,
)


class WeftReader:
    """
    A reader for .weft files that handles block priority and caching.

    Block priority (highest to lowest):
    1. Daily blocks
    2. Monthly blocks
    3. Multi-year blocks
    """

    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize a WeftReader.

        Args:
            file_path: Optional path to a .weft file to load
        """
        self.files: Dict[str, WeftFile] = {}
        if file_path is not None:
            self.load_file(file_path, "default")

    def load_file(self, file_path: str, file_id: str = "default") -> WeftFile:
        """
        Load a .weft file.

        Args:
            file_path: Path to the .weft file
            file_id: Identifier for the loaded file

        Returns:
            The loaded WeftFile instance
        """
        with open(file_path, "rb") as f:
            data = f.read()
        self.files[file_id] = WeftFile.from_bytes(data)
        return self.files[file_id]

    def unload_file(self, file_id: str = "default") -> None:
        """
        Unload a .weft file.

        Args:
            file_id: Identifier of the file to unload
        """
        if file_id in self.files:
            del self.files[file_id]

    def get_info(self, file_id: str) -> dict[str, Union[str, list[BlockType], int]]:
        """
        Get information about a loaded .weft file.

        Args:
            file_id: Identifier of the file to get info for

        Returns:
            Dictionary containing file information

        Raises:
            KeyError: If the file ID is not found
        """
        if file_id not in self.files:
            raise KeyError(f"No file loaded with ID {file_id}")

        return self.files[file_id].get_info()

    def get_date_range(self, file_id: str = "default") -> Tuple[datetime, datetime]:
        """
        Get the date range covered by a loaded .weft file.

        Args:
            file_id: Identifier of the file to get date range for

        Returns:
            Tuple of (start_date, end_date)
        """
        if file_id not in self.files:
            raise KeyError(f"No file loaded with ID {file_id}")

        weft_file = self.files[file_id]
        start_date = None
        end_date = None

        for block in weft_file.blocks:
            if isinstance(block, MultiYearBlock):
                block_start = datetime(block.start_year, 1, 1, tzinfo=timezone.utc)
                block_end = datetime(
                    block.start_year + block.duration, 1, 1, tzinfo=timezone.utc
                )
            elif isinstance(block, MonthlyBlock):
                block_start = datetime(block.year, block.month, 1, tzinfo=timezone.utc)
                # Handle month rollover
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

    def get_value(self, file_id: str, dt: datetime) -> float:
        """
        Get a value from a loaded .weft file for a specific datetime.

        Args:
            file_id: Identifier of the file to get value from
            dt: The datetime to get the value for (timezone-aware or naive)

        Returns:
            The value at the given datetime

        Raises:
            KeyError: If the file ID is not found
            ValueError: If no block covers the given time
        """
        if file_id not in self.files:
            raise KeyError(f"No file loaded with ID {file_id}")

        return self.files[file_id].evaluate(dt)

    def get_value_with_linear_interpolation(
        self, dt: datetime, file_id: Optional[str] = None
    ) -> float:
        """
        Get a value from a loaded .weft file for a specific datetime, always using linear interpolation
        between overlapping blocks.

        Args:
            dt: The datetime to get the value for (timezone-aware or naive)
            file_id: The key used when loading the file

        Returns:
            The interpolated value at the given datetime

        Raises:
            KeyError: If the key is not found
            ValueError: If no block covers the given time
        """
        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # If file_id is None, use the only loaded file
        if file_id is None:
            if len(self.files) != 1:
                raise ValueError(
                    "file_id must be provided when multiple files are loaded"
                )
            file_id = next(iter(self.files.keys()))

        if file_id not in self.files:
            raise KeyError(f"No weft file loaded for key: {file_id}")

        weft_file = self.files[file_id]

        # Find all forty-eight hour blocks that contain this datetime
        forty_eight_hour_blocks: List[FortyEightHourBlock] = []
        for block in weft_file.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                forty_eight_hour_blocks.append(block)

        # If we have forty-eight hour blocks, use them with interpolation
        if forty_eight_hour_blocks:
            # Always use interpolation, even with a single block
            return self._interpolate_forty_eight_hour_blocks(
                forty_eight_hour_blocks, dt, file_id
            )

        # If no forty-eight hour blocks, fall back to regular get_value behavior
        return self.get_value(file_id, dt)

    def _interpolate_forty_eight_hour_blocks(
        self, blocks: List[FortyEightHourBlock], dt: datetime, file_id: str
    ) -> float:
        """
        Interpolate between multiple forty-eight hour blocks.

        When multiple forty-eight hour blocks cover the same datetime, we linearly
        interpolate between them based on their relative influence.

        Args:
            blocks: List of forty-eight hour blocks that contain the datetime
            dt: The datetime to evaluate at
            file_id: The file ID (used to determine angle handling)

        Returns:
            The interpolated value
        """
        # Sort blocks by date
        blocks = sorted(blocks, key=lambda b: b.header.start_day)

        # Calculate midpoints for each block
        midpoints = []
        for block in blocks:
            # Get the midpoint time for this block
            start_time = datetime.combine(
                block.header.start_day, time(12, 0), timezone.utc
            )
            midpoints.append(start_time)

        # Convert midpoints to timestamps for easier calculation
        midpoint_ts = [m.timestamp() for m in midpoints]
        target_ts = dt.timestamp()

        # Calculate weights based on time distance from each block's midpoint
        weights = []
        for i, block in enumerate(blocks):
            # Calculate time distance from block's midpoint in hours
            time_diff = (
                abs(target_ts - midpoint_ts[i]) / 3600
            )  # Convert seconds to hours
            # Weight decreases linearly from 1 at midpoint to 0 at 24 hours away
            weight = max(0.0, 1.0 - time_diff / 24.0)
            weights.append(weight)

        # Normalize weights to sum to 1.0
        weight_sum = sum(weights)
        if weight_sum > 0:
            weights = [w / weight_sum for w in weights]
        else:
            # This shouldn't happen, but provide a fallback
            return self._interpolate_fallback(blocks, dt, file_id)

        # Calculate values from each block
        block_values = []
        for block in blocks:
            block_values.append(block.evaluate(dt))

        # Check if this is a wrapping angle
        if self._is_wrapping_angle(file_id):
            # For wrapping angles, we need to interpolate carefully
            # Get the range of the wrapping behavior
            weft_file = self.files[file_id]
            behavior = cast(RangedBehavior, weft_file.value_behavior)
            min_val, max_val = behavior["range"]
            range_size = max_val - min_val

            # For angles like [0, 360), we need to handle the case where
            # we're interpolating across the wrap boundary
            # First, normalize all values to be within the specified range
            normalized_values = []
            for value in block_values:
                normalized_values.append(min_val + ((value - min_val) % range_size))

            # Check if we're crossing the boundary
            crossing_boundary = False
            for i in range(len(normalized_values)):
                for j in range(i + 1, len(normalized_values)):
                    # If any two values are more than half the range apart,
                    # we're probably crossing the boundary
                    if (
                        abs(normalized_values[i] - normalized_values[j])
                        > range_size / 2
                    ):
                        crossing_boundary = True
                        break

            if crossing_boundary:
                # If crossing boundary, unwrap the values relative to the first value
                reference = normalized_values[0]
                unwrapped_values = []
                for value in normalized_values:
                    # Calculate smallest angular distance
                    diff = (
                        (value - reference + range_size / 2) % range_size
                    ) - range_size / 2
                    unwrapped_values.append(reference + diff)

                # Interpolate using unwrapped values
                value = sum(v * w for v, w in zip(unwrapped_values, weights))

                # Normalize the result back to the original range
                return min_val + ((value - min_val) % range_size)
            else:
                # Not crossing boundary, can use regular interpolation with normalized values
                return sum(v * w for v, w in zip(normalized_values, weights))
        else:
            # For regular non-wrapping values, use standard weighted average
            value = sum(v * w for v, w in zip(block_values, weights))

            # Apply value behavior
            return self.files[file_id].apply_value_behavior(value)

    def _interpolate_remaining_blocks(
        self,
        blocks: List[FortyEightHourBlock],
        block_values: List[float],
        block_x_values: List[float],
        dt: datetime,
        file_id: str,
    ) -> float:
        """
        Fallback interpolation when some blocks are out of valid x range.

        Args:
            blocks: List of blocks to interpolate between
            block_values: List of values from each block
            block_x_values: List of x values for each block
            dt: The datetime to evaluate at
            file_id: The file ID (used to determine angle handling)

        Returns:
            The interpolated value
        """
        valid_indices = [i for i, x in enumerate(block_x_values) if -1 <= x <= 1]

        if not valid_indices:
            return self._interpolate_fallback(blocks, dt, file_id)

        valid_values = [block_values[i] for i in valid_indices]
        valid_x = [block_x_values[i] for i in valid_indices]

        # Calculate weights for valid blocks
        weights = [1 - abs(x) for x in valid_x]
        weight_sum = sum(weights)

        if weight_sum > 0:
            weights = [w / weight_sum for w in weights]
            value = sum(v * w for v, w in zip(valid_values, weights))
            return self.files[file_id].apply_value_behavior(value)
        else:
            return self._interpolate_fallback(blocks, dt, file_id)

    def _interpolate_fallback(
        self, blocks: List[FortyEightHourBlock], dt: datetime, file_id: str
    ) -> float:
        """
        Simple fallback interpolation method.

        Args:
            blocks: List of blocks to interpolate between
            dt: The datetime to evaluate at
            file_id: The file ID (used to determine angle handling)

        Returns:
            The interpolated value
        """
        # Just use the closest block's value
        closest_block = min(
            blocks,
            key=lambda b: abs(
                dt.timestamp()
                - datetime.combine(
                    b.header.start_day, time(), tzinfo=timezone.utc
                ).timestamp()
            ),
        )
        return self.files[file_id].apply_value_behavior(closest_block.evaluate(dt))

    def _is_wrapping_angle(self, file_id: str) -> bool:
        """
        Check if a file contains wrapping angle values.

        Args:
            file_id: The file ID to check

        Returns:
            True if the file contains wrapping angle values
        """
        weft_file = self.files[file_id]
        return weft_file.value_behavior["type"] == "wrapping"

    def get_keys(self) -> List[str]:
        """
        Get a list of all loaded file keys.

        Returns:
            List of keys
        """
        return list(self.files.keys())
