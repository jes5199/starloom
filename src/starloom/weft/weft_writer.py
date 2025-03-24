"""
A class to write .weft binary ephemeris files with multiple levels of precision.

This module provides functionality to write .weft files with century, year, month,
and daily blocks, using Chebyshev polynomials for efficient storage.
"""

from datetime import datetime, timedelta, date, time, timezone
from typing import List, Dict, Tuple, Optional, Any, Union, TypeVar, cast
from zoneinfo import ZoneInfo
import os
from numpy.polynomial import chebyshev
import time as time_module
import numpy as np

from .weft_file import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    BlockType,
    RangedBehavior,
    UnboundedBehavior,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..horizons.parsers import OrbitalElementsQuantity
    from ..horizons.quantities import (
        EphemerisQuantity,
    )

from .ephemeris_data_source import EphemerisDataSource
from .block_selection import (
    should_include_multi_year_block,
    should_include_monthly_block,
    should_include_fourty_eight_hour_block,
)
from .logging import get_logger
from .timespan import descriptive_timespan
from .blocks.utils import unwrap_angles

# Create a logger for this module
logger = get_logger(__name__)

T = TypeVar("T", bound=BlockType)


class WeftWriter:
    """
    A class to write .weft binary ephemeris files with multiple levels of precision.
    This class can create files with century, year, month, and daily blocks.
    """

    def __init__(self, quantity: "EphemerisQuantity"):
        """Initialize the WeftWriter.

        Args:
            quantity: The type of quantity to generate
        """
        from ..horizons.quantities import EphemerisQuantity

        self.quantity = quantity
        self.wrapping_behavior = (
            "wrapping"
            if quantity
            in [
                EphemerisQuantity.ECLIPTIC_LONGITUDE,
                EphemerisQuantity.RIGHT_ASCENSION,
                EphemerisQuantity.APPARENT_AZIMUTH,
            ]
            else "bounded"
        )

        # Initialize value behavior based on quantity
        self.value_behavior = self._initialize_value_behavior()

    def _initialize_value_behavior(self) -> Union[RangedBehavior, UnboundedBehavior]:
        """Initialize the value behavior based on the quantity type.

        Returns:
            A RangedBehavior or UnboundedBehavior instance depending on the quantity
        """
        from ..horizons.quantities import EphemerisQuantity

        if self.wrapping_behavior == "wrapping":
            if self.quantity == EphemerisQuantity.RIGHT_ASCENSION:
                # Right ascension is in hours [0, 24)
                return RangedBehavior(
                    type="wrapping",
                    range=(0.0, 24.0),
                )
            else:
                # Other angles are in degrees [0, 360)
                return RangedBehavior(
                    type="wrapping",
                    range=(0.0, 360.0),
                )
        elif self.quantity == EphemerisQuantity.ECLIPTIC_LATITUDE:
            # Latitude is bounded [-90, 90]
            return RangedBehavior(
                type="bounded",
                range=(-90.0, 90.0),
            )
        elif self.quantity == EphemerisQuantity.PHASE_ANGLE:
            # Phase angle is bounded [0, 180]
            return RangedBehavior(
                type="bounded",
                range=(0.0, 180.0),
            )
        elif self.quantity == EphemerisQuantity.ILLUMINATION:
            # Illumination is bounded [0, 1]
            return RangedBehavior(
                type="bounded",
                range=(0.0, 1.0),
            )
        else:
            # Other quantities are unbounded
            return UnboundedBehavior(type="unbounded")

    def _generate_samples(
        self,
        data_source: EphemerisDataSource,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Tuple[List[float], List[float]]:
        """
        Generate sample points for fitting using all available data points.

        Args:
            data_source: The data source to get values from
            start_dt: Start datetime
            end_dt: End datetime

        Returns:
            Tuple of (x_values, values)
        """
        # Time the timestamp filtering
        filter_start = time_module.time()

        # Use binary search to find indices of start and end timestamps
        # since the timestamps list is sorted
        timestamps = data_source.timestamps

        # Find start index (first timestamp >= start_dt)
        start_idx = 0
        end_idx = len(timestamps) - 1
        while start_idx <= end_idx:
            mid_idx = (start_idx + end_idx) // 2
            if timestamps[mid_idx] < start_dt:
                start_idx = mid_idx + 1
            else:
                end_idx = mid_idx - 1

        # Find end index (last timestamp <= end_dt)
        start_idx_for_end = start_idx
        end_idx = len(timestamps) - 1
        while start_idx_for_end <= end_idx:
            mid_idx = (start_idx_for_end + end_idx) // 2
            if timestamps[mid_idx] <= end_dt:
                start_idx_for_end = mid_idx + 1
            else:
                end_idx = mid_idx - 1

        # Extract the timestamps in range using the found indices
        filtered_timestamps = timestamps[start_idx : end_idx + 1]

        filter_end = time_module.time()
        filter_time_ms = (filter_end - filter_start) * 1000
        logger.debug(
            f"Filtered {len(filtered_timestamps)} timestamps in {filter_time_ms:.2f}ms (binary search)"
        )

        if not filtered_timestamps:
            return [], []

        # Calculate x values for each timestamp
        total_seconds = (end_dt - start_dt).total_seconds()
        x_values = []
        values = []

        # Time the value retrieval and x-value calculation
        value_start = time_module.time()
        for dt in filtered_timestamps:
            # Calculate x value in [-1, 1] range
            elapsed_seconds = (dt - start_dt).total_seconds()
            x = -1.0 + 2.0 * elapsed_seconds / total_seconds
            x_values.append(x)

            # Get value at this time
            value = data_source.get_value_at(dt)  # basically a dictionary lookup
            values.append(value)
        value_end = time_module.time()
        value_time_ms = (value_end - value_start) * 1000
        logger.debug(f"Retrieved {len(values)} values in {value_time_ms:.2f}ms")

        # Handle wrapping behavior if needed
        if self.wrapping_behavior == "wrapping":
            # Get the range from the value behavior
            ranged_behavior = cast(RangedBehavior, self.value_behavior)
            min_val, max_val = ranged_behavior["range"]

            # Unwrap the values
            values = unwrap_angles(values, min_val, max_val)
            logger.debug("Applied angle unwrapping to values")

        # Log total time
        total_time_ms = filter_time_ms + value_time_ms
        logger.debug(f"Total sample generation time: {total_time_ms:.2f}ms")

        return x_values, values

    def _generate_chebyshev_coefficients(
        self,
        data_source: EphemerisDataSource,
        start_dt: datetime,
        end_dt: datetime,
        degree: int,
    ) -> List[float]:
        """
        Generate Chebyshev coefficients for a given time range.

        Args:
            data_source: The data source to get values from
            start_dt: Start datetime
            end_dt: End datetime
            degree: Degree of Chebyshev polynomial to fit

        Returns:
            List of Chebyshev coefficients
        """

        logger.debug(f"Generating coefficients for {start_dt} to {end_dt}")

        # Time the sample generation
        sample_start = time_module.time()
        x_values, values = self._generate_samples(data_source, start_dt, end_dt)
        sample_end = time_module.time()
        sample_time_ms = (sample_end - sample_start) * 1000
        logger.debug(
            f"Generated {len(x_values)} samples for {start_dt} to {end_dt} in {sample_time_ms:.2f}ms"
        )

        # Time the Chebyshev coefficient fitting
        fit_start = time_module.time()
        coeffs = chebyshev.chebfit(x_values, values, deg=degree)
        fit_end = time_module.time()
        fit_time_ms = (fit_end - fit_start) * 1000
        logger.debug(
            f"Fitted Chebyshev coefficients (degree {degree}) in {fit_time_ms:.2f}ms"
        )

        # Convert numpy array to list of float
        try:
            # This is safe because we know coeffs is a numpy array of floats
            coeffs_list = coeffs.tolist()
        except (AttributeError, TypeError):
            # Handle the case where coeffs is not a numpy array
            logger.warning(
                f"Failed to convert coeffs to list using tolist(): {type(coeffs)}"
            )
            try:
                # Try to convert to a list of floats
                coeffs_list = [float(c) for c in coeffs]
            except Exception as e:
                # If all else fails, return a safe default
                logger.error(f"Unable to process coefficients: {e}")
                return [0.0]

        # Define threshold for "very very tiny"
        threshold = 1e-12

        # Ensure coeffs_list is a list we can work with
        if not isinstance(coeffs_list, list):
            logger.warning(
                f"Expected list but got {type(coeffs_list)}, trying conversion"
            )
            try:
                # Convert to list and ensure it's a List[float]
                coeffs_list = cast(List[float], list(coeffs_list))
            except Exception:
                logger.error("Failed to convert to list")
                return [0.0]

        # Trim from the end until we find a coefficient larger than the threshold
        while len(coeffs_list) > 1 and abs(cast(float, coeffs_list[-1])) < threshold:
            coeffs_list.pop()

        # Count how many coefficients we dropped
        if isinstance(coeffs, np.ndarray):
            original_len = len(coeffs)
            current_len = len(coeffs_list)
            if current_len < original_len:
                logger.debug(
                    f"Dropped {original_len - current_len} tiny coefficients below {threshold}"
                )

        logger.debug(f"Coefficients: {coeffs_list}")
        # Ensure we return a List[float] as the function signature promises
        return cast(List[float], coeffs_list)

    def create_multi_year_block(
        self,
        data_source: EphemerisDataSource,
        start_year: int,
        duration: int,
        degree: int,
    ) -> Optional[MultiYearBlock]:
        """
        Create a multi-year block covering the specified years.

        Args:
            data_source: The data source to get values from
            start_year: Starting year
            duration: Number of years to cover
            degree: Degree of Chebyshev polynomial to fit

        Returns:
            A MultiYearBlock or None if coverage criteria not met
        """

        # Check if this block should be included based on coverage criteria
        if not should_include_multi_year_block(data_source, start_year, duration):
            logger.debug(
                f"Multi-year block not included for {start_year}-{start_year + duration - 1}"
            )
            return None

        start_dt = datetime(start_year, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_dt = datetime(start_year + duration, 1, 1, tzinfo=ZoneInfo("UTC"))

        # Generate samples and fit coefficients
        coeffs_list = self._generate_chebyshev_coefficients(
            data_source, start_dt, end_dt, degree
        )

        return MultiYearBlock(
            start_year=start_year, duration=duration, coeffs=coeffs_list
        )

    def create_monthly_blocks(
        self,
        data_source: EphemerisDataSource,
        start_date: datetime,
        end_date: datetime,
        degree: int,
    ) -> List[MonthlyBlock]:
        """
        Create monthly blocks for the specified months.

        Args:
            data_source: The data source to get values from
            start_date: Start date
            end_date: End date (inclusive)
            degree: Degree of Chebyshev polynomial to fit

        Returns:
            List of MonthlyBlock objects
        """
        blocks = []

        year, month = start_date.year, start_date.month

        # Loop until the current month goes past end_date
        while datetime(year, month, 1, tzinfo=start_date.tzinfo) <= end_date:
            month_start = datetime(year, month, 1, tzinfo=start_date.tzinfo)
            # Last day of the month: move to next month and subtract a day
            if month == 12:
                next_month = datetime(year + 1, 1, 1, tzinfo=start_date.tzinfo)
            else:
                next_month = datetime(year, month + 1, 1, tzinfo=start_date.tzinfo)
            month_end = next_month - timedelta(days=1)

            # Adjust boundaries for the overall range
            block_start = max(start_date, month_start)
            block_end = min(end_date, month_end)
            day_count = (block_end - block_start).days + 1

            # Only include if the month meets the criteria
            if should_include_monthly_block(data_source, year, month):
                coeffs_list = self._generate_chebyshev_coefficients(
                    data_source, block_start, block_end, degree
                )
                blocks.append(
                    MonthlyBlock(
                        year=year, month=month, day_count=day_count, coeffs=coeffs_list
                    )
                )

            # Move to the next month
            year = next_month.year
            month = next_month.month

        return blocks

    def create_forty_eight_hour_blocks(
        self,
        data_source: EphemerisDataSource,
        start_date: datetime,
        end_date: datetime,
        degree: int,
    ) -> List[Union[FortyEightHourSectionHeader, FortyEightHourBlock]]:
        # Normalize to day boundaries
        start_date = datetime.combine(start_date.date(), time(0), tzinfo=timezone.utc)
        end_date = datetime.combine(end_date.date(), time(0), tzinfo=timezone.utc)

        # Create blocks and headers as we go
        blocks: List[Union[FortyEightHourSectionHeader, FortyEightHourBlock]] = []

        current_date = start_date

        # Create a temporary list to store blocks before creating the header
        all_blocks = []
        min_block_date = None
        max_block_date = None

        # Process each day in the range
        while current_date <= end_date:
            # Only process dates that pass the coverage criteria
            if should_include_fourty_eight_hour_block(data_source, current_date):
                # Create a block for this date
                block_date = date(
                    current_date.year, current_date.month, current_date.day
                )

                # Track min/max dates from actual included blocks
                if min_block_date is None or block_date < min_block_date:
                    min_block_date = block_date
                if max_block_date is None or block_date > max_block_date:
                    max_block_date = block_date

                # Define the 48-hour window centered at current_date,
                # adjusting for boundaries.
                block_start = max(start_date, current_date - timedelta(days=1))
                block_end = min(end_date, current_date + timedelta(days=1))

                coeffs_list = self._generate_chebyshev_coefficients(
                    data_source, block_start, block_end, degree
                )

                all_blocks.append((block_date, coeffs_list))

            current_date += timedelta(days=1)

        # Skip if no blocks were created
        if all_blocks:
            # Create header using actual min/max dates from included blocks
            header = FortyEightHourSectionHeader(
                start_day=min_block_date,
                end_day=max_block_date,
                block_size=0,  # Will be updated after blocks are created
                block_count=0,  # Will be updated after blocks are created
            )

            # Create the actual blocks with the header
            final_blocks = []
            for block_date, coeffs_list in all_blocks:
                final_blocks.append(
                    FortyEightHourBlock(
                        header=header, coeffs=coeffs_list, center_date=block_date
                    )
                )

            # Calculate block size from the first block
            sample_block = final_blocks[0]
            sample_bytes = sample_block.to_bytes()
            block_size = len(sample_bytes)

            # Update the header with actual block size and count
            header.block_size = block_size
            header.block_count = len(final_blocks)

            # Add the header and all blocks to the result
            blocks.append(header)
            blocks.extend(final_blocks)

        return blocks

    def create_multi_precision_file(
        self,
        data_source: EphemerisDataSource,
        quantity: Union["EphemerisQuantity", "OrbitalElementsQuantity"],
        start_date: datetime,
        end_date: datetime,
        config: Dict[str, Any],
        custom_timespan: Optional[str] = None,
    ) -> WeftFile:
        """
        Create a .weft file with multiple precision levels.

        Args:
            data_source: The data source to get values from
            quantity: The quantity to generate data for
            start_date: Start date
            end_date: End date (inclusive)
            config: Configuration for each block type
            custom_timespan: Optional custom timespan for the file preamble

        Returns:
            A WeftFile instance
        """
        blocks: List[BlockType] = []

        # Add blocks in order of decreasing precision (least precise first)
        if config["multi_year"]["enabled"]:
            multi_year_config = config["multi_year"]

            # Get the time range from the data source
            start_year = data_source.start_date.year
            end_year = data_source.end_date.year

            # Create blocks for each decade in the range
            for decade_start in range(start_year - (start_year % 10), end_year + 1, 10):
                decade_block = self.create_multi_year_block(
                    data_source=data_source,
                    start_year=decade_start,
                    duration=10,
                    degree=multi_year_config["polynomial_degree"],
                )
                if decade_block:
                    blocks.append(decade_block)
                    logger.debug(
                        f"Added decade block for {decade_start}-{decade_start + 9}"
                    )

            # Create blocks for each year in the range
            for year in range(start_year, end_year + 1):
                year_block = self.create_multi_year_block(
                    data_source=data_source,
                    start_year=year,
                    duration=1,
                    degree=multi_year_config["polynomial_degree"],
                )
                if year_block:
                    blocks.append(year_block)
                    logger.debug(f"Added year block for {year}")

        if config["monthly"]["enabled"]:
            monthly_config = config["monthly"]
            # Create monthly blocks for each month in the span
            monthly_blocks = self.create_monthly_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                degree=monthly_config["polynomial_degree"],
            )
            blocks.extend(monthly_blocks)

        if config["forty_eight_hour"]["enabled"]:
            forty_eight_hour_config = config["forty_eight_hour"]
            # Create forty-eight hour blocks for the entire span
            forty_eight_hour_blocks = self.create_forty_eight_hour_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                degree=forty_eight_hour_config["polynomial_degree"],
            )
            # The headers and blocks are already correctly organized
            blocks.extend(forty_eight_hour_blocks)

        # Create preamble
        preamble = self._create_preamble(
            data_source=data_source,
            quantity=quantity,
            start_date=start_date,
            end_date=end_date,
            config=config,
            custom_timespan=custom_timespan,
        )

        return WeftFile(preamble=preamble, blocks=blocks)

    def save_file(self, weft_file: WeftFile, output_path: str) -> None:
        """
        Save a WeftFile to disk.

        Args:
            weft_file: The WeftFile to save
            output_path: Path to save the file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save the file
        weft_file.write_to_file(output_path)

    def _create_preamble(
        self,
        data_source: EphemerisDataSource,
        quantity: Union["EphemerisQuantity", "OrbitalElementsQuantity"],
        start_date: datetime,
        end_date: datetime,
        config: Dict[str, Any],
        custom_timespan: Optional[str] = None,
    ) -> str:
        """
        Create the preamble for a .weft file.

        Args:
            data_source: The data source to get values from
            quantity: The quantity to generate data for
            start_date: Start date
            end_date: End date (inclusive)
            config: Configuration for each block type
            custom_timespan: Optional custom timespan for the file preamble

        Returns:
            The preamble string
        """
        now = datetime.utcnow()

        # Get a human-readable timespan string
        timespan = descriptive_timespan(start_date, end_date, custom_timespan)

        # Add value behavior range to preamble if applicable
        behavior_str = self.wrapping_behavior
        behavior_type = self.value_behavior["type"]
        if behavior_type in ("wrapping", "bounded"):
            # Only access range for RangedBehavior types (not for UnboundedBehavior)
            ranged_behavior = cast(RangedBehavior, self.value_behavior)
            min_val, max_val = ranged_behavior["range"]
            behavior_str = f"{behavior_str}[{min_val},{max_val}]"

        preamble = (
            f"#weft! v0.02 {data_source.planet_id} jpl:horizons {timespan} "
            f"32bit {quantity.name} {behavior_str} chebychevs "
            f"generated@{now.isoformat()}\n\n"
        )

        return preamble
