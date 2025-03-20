from enum import Enum


class EphemType(Enum):
    """Type of ephemeris to generate."""

    OBSERVER = "OBSERVER"
    VECTORS = "VECTORS"
    ELEMENTS = "ELEMENTS"
    SPK = "SPK"
    APPROACH = "APPROACH"
