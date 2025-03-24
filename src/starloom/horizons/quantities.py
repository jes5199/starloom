from enum import Enum
from typing import Optional, List, Dict, Union
from dataclasses import dataclass
import re

from ..ephemeris import Quantity


def normalize_column_name(key: str) -> str:
    """Normalize column name by replacing multiple underscores with a single one.

    Args:
        key: Column name to normalize

    Returns:
        Normalized column name
    """
    return re.sub(r"_+", "_", key.strip())


class HorizonsRequestObserverQuantities(Enum):
    """
    This is what can be put in the URL for the OBSERVER_QUANTITIES parameter
    """

    ASTROMETRIC_RA_DEC = 1
    APPARENT_RA_DEC = 2
    RATES_RA_DEC = 3
    APPARENT_AZ_EL = 4
    RATES_AZ_EL = 5
    XY_SATELLITE_OFFSET = 6
    LOCAL_APPARENT_SIDEREAL_TIME = 7
    AIRMASS_VISUAL_MAGNITUDE_EXTINCTION = 8
    VISUAL_MAGNITUDE_SURFACE_BRIGHTNESS = 9
    ILLUMINATED_FRACTION = 10
    DEFECT_OF_ILLUMINATION = 11
    ANGULAR_SEPARATION_VISIBILITY = 12
    TARGET_ANGULAR_DIAMETER = 13
    OBSERVER_SUB_LONG_LAT = 14
    SOLAR_SUB_LONG_LAT = 15
    SUB_SOLAR_POS_ANGLE_DISTANCE = 16
    NORTH_POLE_POS_ANGLE_DISTANCE = 17
    HELIOCENTRIC_ECLIPTIC_LONG_LAT = 18
    SOLAR_RANGE_RANGE_RATE = 19
    TARGET_RANGE_RANGE_RATE = 20
    DOWN_LEG_LIGHT_TIME = 21
    SPEED_WITH_RESPECT_TO_SUN_OBSERVER = 22
    SOLAR_ELONGATION_ANGLE = 23
    SUN_TARGET_OBSERVER_ANGLE = 24
    TARGET_OBSERVER_MOON_ANGLE_ILLUMINATED_FRACTION = 25
    OBSERVER_PRIMARY_TARGET_ANGLE = 26
    POSITION_ANGLES_HELIOCENTRIC_RADIUS_VELOCITY_VECTOR = 27
    ORBIT_PLANE_ANGLE = 28
    CONSTELLATION_ID = 29
    TDB_UT = 30
    OBSERVER_ECLIPTIC_LONG_LAT = 31
    TARGET_NORTH_POLE_RA_DEC = 32
    GALACTIC_LONG_LAT = 33
    LOCAL_APPARENT_SOLAR_TIME = 34
    EARTH_TO_SITE_LIGHT_TIME = 35
    PLANE_OF_SKY_RA_DEC_POINTING_UNCERTAINTY = 36
    PLANE_OF_SKY_ERROR_ELLIPSE = 37
    PLANE_OF_SKY_ELLIPSE_RSS_POINTING_UNCERTAINTY = 38
    UNCERTAINTIES_PLANE_OF_SKY_RADIAL_DIRECTION = 39
    RADAR_UNCERTAINTIES_PLANE_OF_SKY_RADIAL_DIRECTION = 40
    TRUE_ANOMALY_ANGLE = 41
    LOCAL_APPARENT_HOUR_ANGLE = 42
    PHASE_ANGLE_BISECTOR = 43
    APPARENT_TARGET_CENTERED_LONGITUDE_OF_SUN = 44
    INERTIAL_APPARENT_RA_DEC = 45
    RATE_INERTIAL_RA_DEC = 46
    SKY_MOTION_ANGULAR_RATE_DIRECTION_POSITION_ANGLE_PATH_ANGLE = 47
    SKY_BRIGHTNESS_TARGET_VISUAL_SNR = 48


class HorizonsRequestVectorQuantities(Enum):
    """
    Quantities for vector ephemeris requests to Horizons API
    """
    STATE_VECTOR = 1
    POSITION_ONLY = 2
    VELOCITY_ONLY = 3
    POSITION_COMPONENTS = 4
    VELOCITY_COMPONENTS = 5
    ACCELERATION_COMPONENTS = 6
    SITE_POSITION_COMPONENTS = 7
    SITE_VELOCITY_COMPONENTS = 8


class HorizonsRequestElementsQuantities(Enum):
    """
    Quantities for orbital elements requests to Horizons API
    """
    BASIC_ELEMENTS = 1
    ADDITIONAL_PARAMETERS = 2
    OSCULATING_ELEMENTS = 3
    CARTESIAN_ELEMENTS = 4
    TRANSPORT_ELEMENTS = 5


class EphemerisQuantity(Enum):
    """
    Quantities that can be parsed from Horizons responses.

    This enum is specific to the Horizons API response format and is distinct from
    the more comprehensive Quantity enum in the ephemeris module. Each value
    represents a column name as it appears in Horizons API responses.

    There is a mapping between this enum and the Quantity enum (see QuantityForColumnName),
    allowing for conversion between the API-specific format and the standardized format.
    """

    # Basic identifiers
    BODY = "body"
    DATE_TIME = "Date_(UT)_HR:MN:SC.fff"
    JULIAN_DATE = "JDUT"
    JULIAN_DATE_FRACTION = "JDTDB"

    # Positional quantities
    RIGHT_ASCENSION = "R.A._(ICRF)"
    DECLINATION = "DEC_(ICRF)"
    ECLIPTIC_LONGITUDE = "ObsEcLon"
    ECLIPTIC_LATITUDE = "ObsEcLat"
    APPARENT_AZIMUTH = "Azimuth_(a-app)"
    APPARENT_ELEVATION = "Elevation_(a-app)"

    # Magnitude and brightness
    APPARENT_MAGNITUDE = "APmag"
    SURFACE_BRIGHTNESS = "S-brt"
    ILLUMINATION = "Illu%"

    # Sub-observer and sub-solar points
    OBSERVER_SUB_LON = "ObsSub-LON"
    OBSERVER_SUB_LAT = "ObsSub-LAT"
    SUN_SUB_LON = "SunSub-LON"
    SUN_SUB_LAT = "SunSub-LAT"

    # Angles and distances
    SOLAR_NORTH_ANGLE = "SN.ang"
    SOLAR_NORTH_DISTANCE = "SN.dist"
    NORTH_POLE_ANGLE = "NP.ang"
    NORTH_POLE_DISTANCE = "NP.dist"
    DISTANCE = "delta"
    RANGE_RATE = "deldot"
    PHASE_ANGLE = "phi"
    PHASE_ANGLE_BISECTOR_LON = "PAB-LON"
    PHASE_ANGLE_BISECTOR_LAT = "PAB-LAT"
    ELONGATION = "Elong"

    # Time-related
    LOCAL_APPARENT_SIDEREAL_TIME = "L_Ap_Sid_Time"
    LOCAL_APPARENT_SOLAR_TIME = "L_Ap_SOL_Time"
    LOCAL_APPARENT_HOUR_ANGLE = "r-L_Ap_Hour_Ang"

    # Orbital elements
    ECCENTRICITY = "EC"
    PERIAPSIS_DISTANCE = "QR"
    INCLINATION = "IN"
    ASCENDING_NODE_LONGITUDE = "OM"
    ARGUMENT_OF_PERIFOCUS = "W"
    PERIAPSIS_TIME = "Tp"
    MEAN_MOTION = "N"
    MEAN_ANOMALY = "MA"
    TRUE_ANOMALY = "TA"
    SEMI_MAJOR_AXIS = "A"
    APOAPSIS_DISTANCE = "AD"
    ORBITAL_PERIOD = "PR"

    # Special markers
    SOLAR_PRESENCE_CONDITION_CODE = ""  # First blank column
    TARGET_EVENT_MARKER = ""  # Second blank column


# Create a mapping from EphemerisQuantity to Quantity
EphemerisQuantityToQuantity = {
    EphemerisQuantity.BODY: Quantity.BODY,
    EphemerisQuantity.DATE_TIME: Quantity.DATE_TIME,
    EphemerisQuantity.JULIAN_DATE: Quantity.JULIAN_DATE,
    EphemerisQuantity.JULIAN_DATE_FRACTION: Quantity.JULIAN_DATE_FRACTION,
    EphemerisQuantity.RIGHT_ASCENSION: Quantity.RIGHT_ASCENSION,
    EphemerisQuantity.DECLINATION: Quantity.DECLINATION,
    EphemerisQuantity.ECLIPTIC_LONGITUDE: Quantity.ECLIPTIC_LONGITUDE,
    EphemerisQuantity.ECLIPTIC_LATITUDE: Quantity.ECLIPTIC_LATITUDE,
    EphemerisQuantity.APPARENT_AZIMUTH: Quantity.APPARENT_AZIMUTH,
    EphemerisQuantity.APPARENT_ELEVATION: Quantity.APPARENT_ELEVATION,
    EphemerisQuantity.APPARENT_MAGNITUDE: Quantity.APPARENT_MAGNITUDE,
    EphemerisQuantity.SURFACE_BRIGHTNESS: Quantity.SURFACE_BRIGHTNESS,
    EphemerisQuantity.ILLUMINATION: Quantity.ILLUMINATION,
    EphemerisQuantity.OBSERVER_SUB_LON: Quantity.OBSERVER_SUB_LON,
    EphemerisQuantity.OBSERVER_SUB_LAT: Quantity.OBSERVER_SUB_LAT,
    EphemerisQuantity.SUN_SUB_LON: Quantity.SUN_SUB_LON,
    EphemerisQuantity.SUN_SUB_LAT: Quantity.SUN_SUB_LAT,
    EphemerisQuantity.SOLAR_NORTH_ANGLE: Quantity.SOLAR_NORTH_ANGLE,
    EphemerisQuantity.SOLAR_NORTH_DISTANCE: Quantity.SOLAR_NORTH_DISTANCE,
    EphemerisQuantity.NORTH_POLE_ANGLE: Quantity.NORTH_POLE_ANGLE,
    EphemerisQuantity.NORTH_POLE_DISTANCE: Quantity.NORTH_POLE_DISTANCE,
    EphemerisQuantity.DISTANCE: Quantity.DELTA,
    EphemerisQuantity.RANGE_RATE: Quantity.DELTA_DOT,
    EphemerisQuantity.PHASE_ANGLE: Quantity.PHASE_ANGLE,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LON: Quantity.PHASE_ANGLE_BISECTOR_LON,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LAT: Quantity.PHASE_ANGLE_BISECTOR_LAT,
    EphemerisQuantity.ELONGATION: Quantity.ELONGATION,
    EphemerisQuantity.LOCAL_APPARENT_SIDEREAL_TIME: Quantity.LOCAL_APPARENT_SIDEREAL_TIME,
    EphemerisQuantity.LOCAL_APPARENT_SOLAR_TIME: Quantity.LOCAL_APPARENT_SOLAR_TIME,
    EphemerisQuantity.LOCAL_APPARENT_HOUR_ANGLE: Quantity.LOCAL_APPARENT_HOUR_ANGLE,
    EphemerisQuantity.ECCENTRICITY: Quantity.ECCENTRICITY,
    EphemerisQuantity.PERIAPSIS_DISTANCE: Quantity.PERIAPSIS_DISTANCE,
    EphemerisQuantity.INCLINATION: Quantity.INCLINATION,
    EphemerisQuantity.ASCENDING_NODE_LONGITUDE: Quantity.ASCENDING_NODE_LONGITUDE,
    EphemerisQuantity.ARGUMENT_OF_PERIFOCUS: Quantity.ARGUMENT_OF_PERIFOCUS,
    EphemerisQuantity.PERIAPSIS_TIME: Quantity.PERIAPSIS_TIME,
    EphemerisQuantity.MEAN_MOTION: Quantity.MEAN_MOTION,
    EphemerisQuantity.MEAN_ANOMALY: Quantity.MEAN_ANOMALY,
    EphemerisQuantity.TRUE_ANOMALY: Quantity.TRUE_ANOMALY,
    EphemerisQuantity.SEMI_MAJOR_AXIS: Quantity.SEMI_MAJOR_AXIS,
    EphemerisQuantity.APOAPSIS_DISTANCE: Quantity.APOAPSIS_DISTANCE,
    EphemerisQuantity.ORBITAL_PERIOD: Quantity.ORBITAL_PERIOD,
    EphemerisQuantity.SOLAR_PRESENCE_CONDITION_CODE: Quantity.SOLAR_PRESENCE_CONDITION_CODE,
    EphemerisQuantity.TARGET_EVENT_MARKER: Quantity.TARGET_EVENT_MARKER,
}


# Mapping from Horizons column names to Quantity enum values
QuantityForColumnName = {
    ephemq.value: EphemerisQuantityToQuantity[ephemq]
    for ephemq in EphemerisQuantity
    if ephemq.value  # Skip entries with empty values (special markers)
}

# Also include the special markers (with empty values)
QuantityForColumnName[""] = (
    Quantity.SOLAR_PRESENCE_CONDITION_CODE
)  # This will be overridden by the next line
QuantityForColumnName[""] = (
    Quantity.TARGET_EVENT_MARKER
)  # We'll handle these special cases separately in the parsers


# Mapping from Quantity to HorizonsRequestObserverQuantities
RequestQuantityForQuantity: dict[
    Quantity, Optional[HorizonsRequestObserverQuantities]
] = {
    Quantity.BODY: None,
    Quantity.JULIAN_DATE: None,
    Quantity.DATE_TIME: None,
    Quantity.RIGHT_ASCENSION: HorizonsRequestObserverQuantities.ASTROMETRIC_RA_DEC,
    Quantity.DECLINATION: HorizonsRequestObserverQuantities.ASTROMETRIC_RA_DEC,
    Quantity.ECLIPTIC_LONGITUDE: HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT,
    Quantity.ECLIPTIC_LATITUDE: HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT,
    Quantity.APPARENT_MAGNITUDE: HorizonsRequestObserverQuantities.VISUAL_MAGNITUDE_SURFACE_BRIGHTNESS,
    Quantity.SURFACE_BRIGHTNESS: HorizonsRequestObserverQuantities.VISUAL_MAGNITUDE_SURFACE_BRIGHTNESS,
    Quantity.ILLUMINATION: HorizonsRequestObserverQuantities.ILLUMINATED_FRACTION,
    Quantity.OBSERVER_SUB_LON: HorizonsRequestObserverQuantities.OBSERVER_SUB_LONG_LAT,
    Quantity.OBSERVER_SUB_LAT: HorizonsRequestObserverQuantities.OBSERVER_SUB_LONG_LAT,
    Quantity.SUN_SUB_LON: HorizonsRequestObserverQuantities.SOLAR_SUB_LONG_LAT,
    Quantity.SUN_SUB_LAT: HorizonsRequestObserverQuantities.SOLAR_SUB_LONG_LAT,
    Quantity.SOLAR_NORTH_ANGLE: HorizonsRequestObserverQuantities.SUB_SOLAR_POS_ANGLE_DISTANCE,
    Quantity.SOLAR_NORTH_DISTANCE: HorizonsRequestObserverQuantities.SUB_SOLAR_POS_ANGLE_DISTANCE,
    Quantity.NORTH_POLE_ANGLE: HorizonsRequestObserverQuantities.NORTH_POLE_POS_ANGLE_DISTANCE,
    Quantity.NORTH_POLE_DISTANCE: HorizonsRequestObserverQuantities.NORTH_POLE_POS_ANGLE_DISTANCE,
    Quantity.DELTA: HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE,
    Quantity.DELTA_DOT: HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE,
    Quantity.PHASE_ANGLE: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
    Quantity.PHASE_ANGLE_BISECTOR_LON: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
    Quantity.PHASE_ANGLE_BISECTOR_LAT: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
}


# Map column names to quantities
EphemerisQuantityForColumnName: Dict[str, EphemerisQuantity] = {
    q.value: q for q in EphemerisQuantity if q.value
}


@dataclass
class Quantities:
    """A collection of quantities to request from Horizons."""

    values: List[int]

    def __init__(self, values: Optional[Union[List[int], None]] = None) -> None:
        """Initialize quantities.

        Args:
            values: List of quantity codes to request
        """
        self.values = (
            values
            if values is not None
            else [
                HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value,  # 20
                HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value,  # 31
            ]
        )

    def to_string(self) -> str:
        """Convert quantities to string format for Horizons API.
        If there are multiple quantities, they will be quoted.

        Returns:
            str: Comma-separated list of quantity codes, quoted if multiple
        """
        quantities_str = ",".join(str(v) for v in sorted(set(self.values)))
        # Add single quotes if there's more than one quantity
        if len(self.values) > 1:
            quantities_str = f"'{quantities_str}'"
        return quantities_str

    def __eq__(self, other: object) -> bool:
        """Compare quantities with another object.

        Args:
            other: Object to compare with

        Returns:
            bool: True if equal, False otherwise
        """
        if isinstance(other, list):
            return self.values == other
        if isinstance(other, Quantities):
            return self.values == other.values
        return NotImplemented


# Add ANGLE_QUANTITIES after the EphemerisQuantity class definition
# This should be a set of quantities that represent angles

# Set of quantities that represent angles and need to be handled specially
ANGLE_QUANTITIES = {
    EphemerisQuantity.RIGHT_ASCENSION,
    EphemerisQuantity.DECLINATION,
    EphemerisQuantity.ECLIPTIC_LONGITUDE,
    EphemerisQuantity.ECLIPTIC_LATITUDE,
    EphemerisQuantity.APPARENT_AZIMUTH,
    EphemerisQuantity.APPARENT_ELEVATION,
}
