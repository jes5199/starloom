"""
Weft binary ephemeris format module.

This module provides tools for reading and generating .weft files,
which store ephemeris data as Chebyshev polynomials for efficient
storage and fast evaluation.
"""

from .blocks.utils import evaluate_chebyshev, unwrap_angles
from .weft import (
    WeftFile,
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
)

from .weft_reader import WeftReader
from .weft_writer import WeftWriter
from .ephemeris_weft_generator import generate_weft_file

__all__ = [
    "WeftFile",
    "MultiYearBlock",
    "MonthlyBlock",
    "FortyEightHourSectionHeader",
    "FortyEightHourBlock",
    "evaluate_chebyshev",
    "unwrap_angles",
    "WeftReader",
    "WeftWriter",
    "generate_weft_file",
]
