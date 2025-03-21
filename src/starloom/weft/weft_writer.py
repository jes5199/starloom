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
        if self.wrapping_behavior == "wrapping":
            if quantity == EphemerisQuantity.RIGHT_ASCENSION:
                # Right ascension is in hours [0, 24)
                self.value_behavior: Union[RangedBehavior, UnboundedBehavior] = (
                    RangedBehavior(
                        type="wrapping",
                        range=(0.0, 24.0),
                    )
                )
            else:
                # Other angles are in degrees [0, 360)
                self.value_behavior = RangedBehavior(
                    type="wrapping",
                    range=(0.0, 360.0),
                )
        elif quantity == EphemerisQuantity.ECLIPTIC_LATITUDE:
            # Latitude is bounded [-90, 90]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(-90.0, 90.0),
            )
        elif quantity == EphemerisQuantity.PHASE_ANGLE:
            # Phase angle is bounded [0, 180]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 180.0),
            )
        elif quantity == EphemerisQuantity.ILLUMINATED_FRACTION:
            # Illumination is bounded [0, 1]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 1.0),
            )
        else:
            # Other quantities are unbounded
            self.value_behavior = UnboundedBehavior(type="unbounded")

    def _generate_samples(
        self,
        data_source: EphemerisDataSource,
        start_dt: datetime,
        end_dt: datetime,
        sample_count: int,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> Tuple[List[float], List[float]]:
        """
        Generate sample points for fitting.

        Args:
            data_source: The data source to get values from
            start_dt: Start datetime
            end_dt: End datetime
            sample_count: Number of sample points to generate
            quantity: Optional quantity override

        Returns:
            Tuple of (x_values, values)
        """
        # Generate evenly spaced sample points
        total_seconds = (end_dt - start_dt).total_seconds()
        step_seconds = total_seconds / (sample_count - 1)

        x_values = []
        values = []

        # Generate samples
        for i in range(sample_count):
            # Calculate x value in [-1, 1] range
            x = -1.0 + 2.0 * i / (sample_count - 1)
            x_values.append(x)

            # Calculate datetime for this sample
            current_dt = start_dt + timedelta(seconds=i * step_seconds)
            # Ensure we don't exceed the data range
            if current_dt > end_dt:
                current_dt = end_dt

            # Get value at this time
            value = data_source.get_value_at(current_dt)
            values.append(value)

        return x_values, values

    def create_multi_year_block(
        self,
        data_source: EphemerisDataSource,
        start_year: int,
        duration: int,
        samples_per_year: int,
        degree: int,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
    ) -> MultiYearBlock:
        """
        Create a multi-year block covering the specified years.

        Args:
            data_source: The data source to get values from
            start_year: Starting year
            duration: Number of years to cover
            samples_per_year: Number of sample points per year
            degree: Degree of Chebyshev polynomial to fit
            quantity: The quantity being computed

        Returns:
            A MultiYearBlock
        """
        start_dt = datetime(start_year, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_dt = datetime(start_year + duration, 1, 1, tzinfo=ZoneInfo("UTC"))

        sample_count = samples_per_year * duration
        x_values, values = self._generate_samples(
            data_source, start_dt, end_dt, sample_count, quantity
        )

        # Fit Chebyshev coefficients
        coeffs = chebyshev.chebfit(x_values, values, deg=degree)
        coeffs_list = cast(List[float], coeffs.tolist())

        return MultiYearBlock(
            start_year=start_year, duration=duration, coeffs=coeffs_list
        )

    def create_monthly_blocks(
        self,
        data_source: EphemerisDataSource,
        start_date: datetime,
        end_date: datetime,
        samples_per_day: int,
        degree: int,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> List[MonthlyBlock]:
        """
        Create monthly blocks for the specified months.

        Args:
            data_source: The data source to get values from
            start_date: Start date
            end_date: End date (inclusive)
            samples_per_day: Number of sample points per day
            degree: Degree of Chebyshev polynomial to fit
            quantity: Optional quantity override

        Returns:
            List of MonthlyBlock objects
        """
        blocks = []

        # Calculate month range
        current_date = datetime(
            start_date.year, start_date.month, 1, tzinfo=ZoneInfo("UTC")
        )
        while current_date < end_date:
            # Calculate days in month
            if current_date.month == 12:
                next_month = datetime(
                    current_date.year + 1, 1, 1, tzinfo=ZoneInfo("UTC")
                )
            else:
                next_month = datetime(
                    current_date.year, current_date.month + 1, 1, tzinfo=ZoneInfo("UTC")
                )

            # If this is the last month and we have an end date, use it
            block_end = next_month
            if block_end > end_date:
                block_end = end_date

            day_count = (next_month - current_date).days

            # Generate samples
            x_values, values = self._generate_samples(
                data_source,
                current_date,
                block_end - timedelta(microseconds=1),
                samples_per_day * day_count,
                quantity,
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            blocks.append(
                MonthlyBlock(
                    year=current_date.year,
                    month=current_date.month,
                    day_count=day_count,
                    coeffs=coeffs_list,
                )
            )

            current_date = next_month

        return blocks

    def create_forty_eight_hour_blocks(
        self,
        data_source: EphemerisDataSource,
        start_date: datetime,
        end_date: datetime,
        samples_per_day: int,
        degree: int,
        block_size: Optional[int] = None,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> List[Union[FortyEightHourSectionHeader, FortyEightHourBlock]]:
        """
        Create a section of forty-eight hour blocks with a single header.

        Args:
            data_source: The data source to get values from
            start_date: Start date
            end_date: End date (inclusive)
            samples_per_day: Number of sample points per day
            degree: Degree of Chebyshev polynomial to fit
            block_size: Fixed size for each block (computed if None)
            quantity: Optional quantity override

        Returns:
            List containing one FortyEightHourSectionHeader followed by FortyEightHourBlocks
        """
        # Ensure we're working with dates at day boundaries
        start_date = datetime(
            start_date.year, start_date.month, start_date.day, tzinfo=ZoneInfo("UTC")
        )
        end_date = datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=ZoneInfo("UTC")
        )

        # If block_size not specified, compute it based on coefficient count
        if block_size is None:
            # Header bytes: marker(2) + year(2) + month(1) + day(1) = 6 bytes
            header_size = 6
            # Each coefficient is a 4-byte float
            coeff_size = (degree + 1) * 4
            # Add padding for alignment (to 16 bytes)
            block_size = header_size + coeff_size
            if block_size % 16 != 0:
                block_size += 16 - (block_size % 16)

        blocks = []
        current_date = start_date
        while (
            current_date < end_date
        ):  # Changed from <= to < to avoid going past end_date
            # Create a header for this block
            block_date = date(current_date.year, current_date.month, current_date.day)
            next_date = block_date + timedelta(days=1)
            header = FortyEightHourSectionHeader(
                start_day=block_date,
                end_day=next_date,  # End day must be after start day
            )
            blocks.append(header)

            # Generate samples for this 48-hour period centered at current_date
            block_start = current_date - timedelta(days=1)  # Start 24h before midnight
            block_end = current_date + timedelta(days=1)  # End 24h after midnight

            # Adjust if we're at the boundaries of our data
            if block_start < start_date:
                block_start = start_date
            if block_end > end_date:
                block_end = end_date

            # Generate samples for this 48-hour period
            x_values, values = self._generate_samples(
                data_source,
                block_start,
                block_end,
                samples_per_day,
                quantity,
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            # Pad coefficients to fixed size if needed
            if block_size is not None:
                coeff_size = block_size - 6  # Subtract header size
                coeff_count = coeff_size // 4  # Each coefficient is 4 bytes
                while len(coeffs_list) < coeff_count:
                    coeffs_list.append(0.0)

            blocks.append(
                FortyEightHourBlock(
                    header=header,  # Use this block's header
                    coeffs=coeffs_list,
                )
            )

            current_date += timedelta(days=1)

        return blocks

    def create_multi_precision_file(
        self,
        data_source: EphemerisDataSource,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
        start_date: datetime,
        end_date: datetime,
        config: Dict[str, Any],
    ) -> WeftFile:
        """
        Create a .weft file with multiple precision levels.

        Args:
            data_source: The data source to get values from
            quantity: The quantity to generate data for
            start_date: Start date
            end_date: End date (inclusive)
            config: Configuration for each block type

        Returns:
            A WeftFile instance
        """
        blocks = []

        # Add blocks in order of decreasing precision (least precise first)
        if config["multi_year"]["enabled"]:
            multi_year_config = config["multi_year"]
            # Create multi-year blocks for the entire span
            multi_year_blocks = self.create_multi_year_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                samples_per_day=multi_year_config["sample_count"],
                degree=multi_year_config["polynomial_degree"],
                quantity=quantity,
            )
            blocks.extend(multi_year_blocks)

        if config["monthly"]["enabled"]:
            monthly_config = config["monthly"]
            # Create monthly blocks for each month in the span
            monthly_blocks = self.create_monthly_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                samples_per_day=monthly_config["sample_count"],
                degree=monthly_config["polynomial_degree"],
                quantity=quantity,
            )
            blocks.extend(monthly_blocks)

        if config["forty_eight_hour"]["enabled"]:
            forty_eight_hour_config = config["forty_eight_hour"]
            # Create forty-eight hour blocks for the entire span
            forty_eight_hour_blocks = self.create_forty_eight_hour_blocks(
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                samples_per_day=forty_eight_hour_config["sample_count"],
                degree=forty_eight_hour_config["polynomial_degree"],
                quantity=quantity,
            )
            # The first block is the header, followed by the actual blocks
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
    ) -> str:
        """
        Create the preamble for a .weft file.

        Args:
            data_source: The data source to get values from
            quantity: The quantity to generate data for
            start_date: Start date
            end_date: End date (inclusive)
            config: Configuration for each block type

        Returns:
            The preamble string
        """
        now = datetime.utcnow()
        timespan = f"{start_date.year}-{end_date.year}"

        # Add value behavior range to preamble if applicable
        behavior_str = self.wrapping_behavior
        if self.value_behavior["type"] in ("wrapping", "bounded"):
            min_val, max_val = self.value_behavior["range"]
            behavior_str = f"{behavior_str}[{min_val},{max_val}]"

        preamble = (
            f"#weft! v0.02 {data_source.planet_id} jpl:horizons {timespan} "
            f"32bit {quantity.name} {behavior_str} chebychevs "
            f"generated@{now.isoformat()}\n\n"
        )

        return preamble
