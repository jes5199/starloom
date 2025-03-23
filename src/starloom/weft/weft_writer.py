"""
A class to write .weft binary ephemeris files with multiple levels of precision.

This module provides functionality to write .weft files with century, year, month,
and daily blocks, using Chebyshev polynomials for efficient storage.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional, Any, Union, TypeVar, cast
from zoneinfo import ZoneInfo
import os
from numpy.polynomial import chebyshev

from .weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    BlockType,
    RangedBehavior,
    UnboundedBehavior,
)
from ..horizons.quantities import (
    EphemerisQuantity,
)
from ..horizons.parsers import OrbitalElementsQuantity
from .ephemeris_data_source import EphemerisDataSource
from .block_selection import (
    should_include_multi_year_block,
    should_include_monthly_block,
    should_include_fourty_eight_hour_block,
)
from .logging import get_logger
from .timespan import descriptive_timespan

# Create a logger for this module
logger = get_logger(__name__)

T = TypeVar("T", bound=BlockType)


class WeftWriter:
    """
    A class to write .weft binary ephemeris files with multiple levels of precision.
    This class can create files with century, year, month, and daily blocks.
    """

    def __init__(self, quantity: EphemerisQuantity):
        """Initialize the WeftWriter.

        Args:
            quantity: The type of quantity to generate
        """
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
            sample_count: Number of sample points to generate (ignored when using all data points)
            quantity: Optional quantity override

        Returns:
            Tuple of (x_values, values)
        """
        # Get all timestamps within the range
        timestamps = [dt for dt in data_source.timestamps if start_dt <= dt <= end_dt]

        if not timestamps:
            return [], []

        # Calculate x values for each timestamp
        total_seconds = (end_dt - start_dt).total_seconds()
        x_values = []
        values = []

        for dt in timestamps:
            # Calculate x value in [-1, 1] range
            elapsed_seconds = (dt - start_dt).total_seconds()
            x = -1.0 + 2.0 * elapsed_seconds / total_seconds
            x_values.append(x)

            # Get value at this time
            value = data_source.get_value_at(dt)
            values.append(value)

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
        # Generate samples
        x_values, values = self._generate_samples(data_source, start_dt, end_dt)

        # Fit Chebyshev coefficients
        coeffs = chebyshev.chebfit(x_values, values, deg=degree)
        return cast(List[float], coeffs.tolist())

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
        start_date = datetime(
            start_date.year, start_date.month, start_date.day, tzinfo=ZoneInfo("UTC")
        )
        end_date = datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=ZoneInfo("UTC")
        )

        blocks = []
        current_date = start_date
        while current_date < end_date:
            # Only process dates that pass the coverage criteria
            if should_include_fourty_eight_hour_block(data_source, current_date):
                block_date = date(
                    current_date.year, current_date.month, current_date.day
                )
                next_date = block_date + timedelta(days=1)
                header = FortyEightHourSectionHeader(
                    start_day=block_date,
                    end_day=next_date,
                )
                blocks.append(header)

                # Define the 48-hour window centered at current_date,
                # adjusting for boundaries.
                block_start = max(start_date, current_date - timedelta(days=1))
                block_end = min(end_date, current_date + timedelta(days=1))

                coeffs_list = self._generate_chebyshev_coefficients(
                    data_source, block_start, block_end, degree
                )

                blocks.append(FortyEightHourBlock(header=header, coeffs=coeffs_list))

            current_date += timedelta(days=1)

        return blocks

    def create_multi_precision_file(
        self,
        data_source: EphemerisDataSource,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
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
            # The first block is the header, followed by the actual blocks
            if forty_eight_hour_blocks:
                header = forty_eight_hour_blocks[0]
                data_blocks = forty_eight_hour_blocks[1:]
                blocks.append(header)  # Add header first
                blocks.extend(data_blocks)  # Then add all blocks

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
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
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
