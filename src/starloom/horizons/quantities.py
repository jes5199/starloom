from enum import Enum
from typing import Optional, List
from dataclasses import dataclass

from ..ephemeris import Quantity


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


# Mapping from Horizons column names to Quantity enum values
QuantityForColumnName = {
    # Basic identifiers
    "body": Quantity.BODY,
    "Date_(UT)_HR:MN:SC.fff": Quantity.DATE_TIME,
    "Date_JDUT": Quantity.JULIAN_DATE,
    "JDTDB": Quantity.JULIAN_DATE_FRACTION,
    # Positional quantities
    "R.A._(ICRF)": Quantity.RIGHT_ASCENSION,
    "DEC_(ICRF)": Quantity.DECLINATION,
    "ObsEcLon": Quantity.ECLIPTIC_LONGITUDE,
    "ObsEcLat": Quantity.ECLIPTIC_LATITUDE,
    "Azimuth_(a-app)": Quantity.APPARENT_AZIMUTH,
    "Elevation_(a-app)": Quantity.APPARENT_ELEVATION,
    # Magnitude and brightness
    "APmag": Quantity.APPARENT_MAGNITUDE,
    "S-brt": Quantity.SURFACE_BRIGHTNESS,
    "Illu%": Quantity.ILLUMINATION,
    # Sub-observer and sub-solar points
    "ObsSub-LON": Quantity.OBSERVER_SUB_LON,
    "ObsSub-LAT": Quantity.OBSERVER_SUB_LAT,
    "SunSub-LON": Quantity.SUN_SUB_LON,
    "SunSub-LAT": Quantity.SUN_SUB_LAT,
    # Angles and distances
    "SN.ang": Quantity.SOLAR_NORTH_ANGLE,
    "SN.dist": Quantity.SOLAR_NORTH_DISTANCE,
    "NP.ang": Quantity.NORTH_POLE_ANGLE,
    "NP.dist": Quantity.NORTH_POLE_DISTANCE,
    "delta": Quantity.DELTA,
    "deldot": Quantity.DELTA_DOT,
    "phi": Quantity.PHASE_ANGLE,
    "PAB-LON": Quantity.PHASE_ANGLE_BISECTOR_LON,
    "PAB-LAT": Quantity.PHASE_ANGLE_BISECTOR_LAT,
    "Elong": Quantity.ELONGATION,
    # Time-related
    "L_Ap_Sid_Time": Quantity.LOCAL_APPARENT_SIDEREAL_TIME,
    "L_Ap_SOL_Time": Quantity.LOCAL_APPARENT_SOLAR_TIME,
    "r-L_Ap_Hour_Ang": Quantity.LOCAL_APPARENT_HOUR_ANGLE,
    # Orbital elements
    "EC": Quantity.ECCENTRICITY,
    "QR": Quantity.PERIAPSIS_DISTANCE,
    "IN": Quantity.INCLINATION,
    "OM": Quantity.ASCENDING_NODE_LONGITUDE,
    "W": Quantity.ARGUMENT_OF_PERIFOCUS,
    "Tp": Quantity.PERIAPSIS_TIME,
    "N": Quantity.MEAN_MOTION,
    "MA": Quantity.MEAN_ANOMALY,
    "TA": Quantity.TRUE_ANOMALY,
    "A": Quantity.SEMI_MAJOR_AXIS,
    "AD": Quantity.APOAPSIS_DISTANCE,
    "PR": Quantity.ORBITAL_PERIOD,
}


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


@dataclass
class Quantities:
    """A collection of quantities to request from Horizons."""

    values: List[int]

    def __init__(self, values: Optional[List[int]] = None) -> None:
        """Initialize quantities.

        Args:
            values: List of quantity codes to request
        """
        self.values = values or []

    def to_string(self) -> str:
        """Convert quantities to string format for Horizons API.

        Returns:
            str: Comma-separated list of quantity codes
        """
        return ",".join(str(v) for v in sorted(set(self.values)))

    def __eq__(self, other: object) -> bool:
        """Compare quantities with another object.

        Args:
            other: Object to compare with

        Returns:
            bool: True if equal, False otherwise
        """
        if isinstance(other, list):
            return list(self.values) == other
        if isinstance(other, Quantities):
            return self.values == other.values
        return NotImplemented
