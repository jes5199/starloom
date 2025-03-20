from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any, cast
from .weft import (
    WeftFile,
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourBlock,
    RangedBehavior,
)
from ..horizons.quantities import EphemerisQuantity


class WeftReader:
    """
    A reader for .weft files that handles block priority and caching.

    Block priority (highest to lowest):
    1. Daily blocks
    2. Monthly blocks
    3. Multi-year blocks
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        file_id: Optional[str] = None,
        quantity: Optional[EphemerisQuantity] = None,
    ) -> None:
        """Initialize a WeftReader instance."""
        self.files: Dict[str, WeftFile] = {}  # Map of file_id to WeftFile
        self.quantity_map: Dict[
            str, EphemerisQuantity
        ] = {}  # Map of file_id to quantity

        # If file_path is provided, load it
        if file_path is not None and file_id is not None:
            self.load_file(file_path, file_id, quantity)

    def load_file(
        self,
        file_path: str,
        file_id: str,
        quantity: Optional[EphemerisQuantity] = None,
    ) -> None:
        """
        Load a .weft file and associate it with a file ID.

        Args:
            file_path: Path to the .weft file
            file_id: ID to associate with this file
            quantity: The quantity stored in this file (for angle normalization)
        """
        self.files[file_id] = WeftFile.from_file(file_path)
        if quantity is not None:
            self.quantity_map[file_id] = quantity

    def get_value(self, dt: datetime, file_id: Optional[str] = None) -> float:
        """
        Get a value from a loaded .weft file for a specific datetime.

        Args:
            dt: The datetime to get the value for (timezone-aware or naive)
            file_id: The key used when loading the file

        Returns:
            The value at the given datetime

        Raises:
            KeyError: If the key is not found
            ValueError: If no block covers the given time
        """
        # If file_id is None, use the only loaded file
        if file_id is None:
            if len(self.files) != 1:
                raise ValueError(
                    "file_id must be provided when multiple files are loaded"
                )
            file_id = next(iter(self.files.keys()))

        # Convert to UTC if timezone-aware, or assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        if file_id not in self.files:
            raise KeyError(f"No weft file loaded for key: {file_id}")

        weft_file = self.files[file_id]

        # Find the block that contains this datetime
        value: Optional[float] = None

        # Try daily blocks first (highest priority)
        daily_blocks: List[FortyEightHourBlock] = []
        for block in weft_file.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                daily_blocks.append(block)

        # If we have daily blocks, use them
        if daily_blocks:
            # If multiple daily blocks cover this datetime, use linear interpolation
            if len(daily_blocks) > 1:
                return self._interpolate_daily_blocks(daily_blocks, dt, file_id)
            else:
                value = daily_blocks[0].evaluate(dt)
        else:
            # Try monthly blocks next
            for block in weft_file.blocks:
                if isinstance(block, MonthlyBlock) and block.contains(dt):
                    value = block.evaluate(dt)
                    break

            # Finally, try multi-year blocks
            if value is None:
                for block in weft_file.blocks:
                    if isinstance(block, MultiYearBlock) and block.contains(dt):
                        value = block.evaluate(dt)
                        break

        if value is None:
            raise ValueError(f"No block found for datetime: {dt}")

        # Apply value behavior
        return weft_file.apply_value_behavior(value)

    def _interpolate_daily_blocks(
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
        blocks = sorted(blocks, key=lambda b: (b.year, b.month, b.day))

        # Calculate midpoints for each block
        midpoints = []
        for block in blocks:
            # The midpoint of a forty-eight hour block is midnight UTC on the specified day
            midpoint = datetime(
                block.year, block.month, block.day, 0, 0, 0, tzinfo=timezone.utc
            )
            midpoints.append(midpoint)

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
                - datetime(
                    b.year, b.month, b.day, 0, 0, 0, tzinfo=timezone.utc
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

    def unload_file(self, key: str) -> None:
        """
        Unload a .weft file from memory.

        Args:
            key: The key used when loading the file
        """
        if key in self.files:
            del self.files[key]
        if key in self.quantity_map:
            del self.quantity_map[key]

    def get_keys(self) -> List[str]:
        """
        Get a list of all loaded file keys.

        Returns:
            List of keys
        """
        return list(self.files.keys())

    def get_date_range(self, key: str) -> Tuple[datetime, datetime]:
        """
        Get the full date range covered by a loaded file.

        Args:
            key: The key of the loaded .weft file

        Returns:
            Tuple of (start_date, end_date)

        Raises:
            KeyError: If the key is not found
        """
        if key not in self.files:
            raise KeyError(f"No weft file loaded for key: {key}")

        weft_file = self.files[key]

        # Find min start date and max end date across all blocks
        min_start = None
        max_end = None

        for block in weft_file.blocks:
            if isinstance(block, MultiYearBlock):
                start = datetime(block.start_year, 1, 1)
                end = datetime(block.start_year + block.duration, 1, 1)
                if min_start is None or start < min_start:
                    min_start = start
                if max_end is None or end > max_end:
                    max_end = end
            elif isinstance(block, MonthlyBlock):
                start = datetime(block.year, block.month, 1)
                # Calculate end date based on month and day count
                if block.month == 12:
                    end = datetime(block.year + 1, 1, 1)
                else:
                    end = datetime(block.year, block.month + 1, 1)

                if min_start is None or start < min_start:
                    min_start = start
                if max_end is None or end > max_end:
                    max_end = end
            elif isinstance(block, FortyEightHourBlock):
                start = datetime(block.year, block.month, block.day)
                end = datetime(block.year, block.month, block.day, 23, 59, 59)
                if min_start is None or start < min_start:
                    min_start = start
                if max_end is None or end > max_end:
                    max_end = end

        if min_start is None or max_end is None:
            raise ValueError("No date range information found in the file")

        return min_start, max_end

    def get_info(self, key: str) -> Dict[str, Any]:
        """
        Get information about a loaded .weft file.

        Args:
            key: The key of the loaded .weft file

        Returns:
            Dictionary of information

        Raises:
            KeyError: If the key is not found
        """
        if key not in self.files:
            raise KeyError(f"No weft file loaded for key: {key}")

        weft_file = self.files[key]

        # Count block types
        multi_year_count = sum(
            1 for block in weft_file.blocks if isinstance(block, MultiYearBlock)
        )
        monthly_count = sum(
            1 for block in weft_file.blocks if isinstance(block, MonthlyBlock)
        )
        daily_count = sum(
            1 for block in weft_file.blocks if isinstance(block, FortyEightHourBlock)
        )

        # Get date range
        date_range = self.get_date_range(key)

        return {
            "preamble": weft_file.preamble,
            "value_behavior": weft_file.value_behavior,
            "block_count": len(weft_file.blocks),
            "multi_year_blocks": multi_year_count,
            "monthly_blocks": monthly_count,
            "daily_blocks": daily_count,
            "start_date": date_range[0],
            "end_date": date_range[1],
        }

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

        # Find all daily blocks that contain this datetime
        daily_blocks: List[FortyEightHourBlock] = []
        for block in weft_file.blocks:
            if isinstance(block, FortyEightHourBlock) and block.contains(dt):
                daily_blocks.append(block)

        # If we have daily blocks, use them with interpolation
        if daily_blocks:
            # Always use interpolation, even with a single block
            return self._interpolate_daily_blocks(daily_blocks, dt, file_id)

        # If no daily blocks, fall back to regular get_value behavior
        return self.get_value(dt, file_id)
