from enum import Enum
import re
from typing import Optional


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


class EphemerisQuantity(Enum):
    """
    Let's give these SQL-friendly names
    """

    BODY = "body"
    JULIAN_DATE = "julian_date"
    DATE_TIME = "date_time"
    RIGHT_ASCENSION = "right_ascension"
    DECLINATION = "declination"
    ECLIPTIC_LONGITUDE = "ecliptic_longitude"
    ECLIPTIC_LATITUDE = "ecliptic_latitude"
    APPARENT_MAGNITUDE = "apparent_magnitude"
    SURFACE_BRIGHTNESS = "surface_brightness"
    ILLUMINATION = "illumination"
    OBSERVER_SUB_LON = "observer_sub_lon"
    OBSERVER_SUB_LAT = "observer_sub_lat"
    SUN_SUB_LON = "sun_sub_lon"
    SUN_SUB_LAT = "sun_sub_lat"
    SOLAR_NORTH_ANGLE = "solar_north_angle"
    SOLAR_NORTH_DISTANCE = "solar_north_distance"
    NORTH_POLE_ANGLE = "north_pole_angle"
    NORTH_POLE_DISTANCE = "north_pole_distance"
    DELTA = "delta"
    DELTA_DOT = "delta_dot"
    PHASE_ANGLE = "phase_angle"
    PHASE_ANGLE_BISECTOR_LON = "phase_angle_bisector_lon"
    PHASE_ANGLE_BISECTOR_LAT = "phase_angle_bisector_lat"
    APPARENT_AZIMUTH = "apparent_azimuth"
    APPARENT_ELEVATION = "apparent_elevation"
    LOCAL_APPARENT_SIDEREAL_TIME = "local_apparent_sidereal_time"
    LOCAL_APPARENT_SOLAR_TIME = "local_apparent_solar_time"
    LOCAL_APPARENT_HOUR_ANGLE = "local_apparent_hour_angle"
    SOLAR_PRESENCE_CONDITION_CODE = "solar_presence_condition_code"
    TARGET_EVENT_MARKER = "target_event_marker"
    HELIOCENTRIC_ECLIPTIC_LONGITUDE = "heliocentric_ecliptic_longitude"
    ELONGATION = "elongation"


class OrbitalElementsQuantity(Enum):
    """
    Enumeration of orbital elements quantities from Horizons
    """

    BODY = "body"
    JULIAN_DATE = "julian_date"
    JULIAN_DATE_FRACTION = "julian_date_fraction"
    ECCENTRICITY = "eccentricity"
    PERIAPSIS_DISTANCE = "periapsis_distance"
    INCLINATION = "inclination"
    ASCENDING_NODE_LONGITUDE = "ascending_node_longitude"
    ARGUMENT_OF_PERIFOCUS = "argument_of_perifocus"
    PERIAPSIS_TIME = "periapsis_time"
    MEAN_MOTION = "mean_motion"
    MEAN_ANOMALY = "mean_anomaly"
    TRUE_ANOMALY = "true_anomaly"
    SEMI_MAJOR_AXIS = "semi_major_axis"
    APOAPSIS_DISTANCE = "apoapsis_distance"
    ORBITAL_PERIOD = "orbital_period"


def normalize_column_name(key: str) -> str:
    return re.sub(r"_+", "_", key.strip())


EphemerisQuantityForColumnName = {
    "body": EphemerisQuantity.BODY,
    "Date_(UT)_HR:MN:SC.fff": EphemerisQuantity.DATE_TIME,
    "Date_JDUT": EphemerisQuantity.JULIAN_DATE,
    "R.A._(ICRF)": EphemerisQuantity.RIGHT_ASCENSION,
    "DEC_(ICRF)": EphemerisQuantity.DECLINATION,
    "ObsEcLon": EphemerisQuantity.ECLIPTIC_LONGITUDE,
    "ObsEcLat": EphemerisQuantity.ECLIPTIC_LATITUDE,
    "APmag": EphemerisQuantity.APPARENT_MAGNITUDE,
    "S-brt": EphemerisQuantity.SURFACE_BRIGHTNESS,
    "Illu%": EphemerisQuantity.ILLUMINATION,
    "ObsSub-LON": EphemerisQuantity.OBSERVER_SUB_LON,
    "ObsSub-LAT": EphemerisQuantity.OBSERVER_SUB_LAT,
    "SunSub-LON": EphemerisQuantity.SUN_SUB_LON,
    "SunSub-LAT": EphemerisQuantity.SUN_SUB_LAT,
    "SN.ang": EphemerisQuantity.SOLAR_NORTH_ANGLE,
    "SN.dist": EphemerisQuantity.SOLAR_NORTH_DISTANCE,
    "NP.ang": EphemerisQuantity.NORTH_POLE_ANGLE,
    "NP.dist": EphemerisQuantity.NORTH_POLE_DISTANCE,
    "delta": EphemerisQuantity.DELTA,
    "deldot": EphemerisQuantity.DELTA_DOT,
    "phi": EphemerisQuantity.PHASE_ANGLE,
    "PAB-LON": EphemerisQuantity.PHASE_ANGLE_BISECTOR_LON,
    "PAB-LAT": EphemerisQuantity.PHASE_ANGLE_BISECTOR_LAT,
    "Azimuth_(a-app)": EphemerisQuantity.APPARENT_AZIMUTH,
    "Elevation_(a-app)": EphemerisQuantity.APPARENT_ELEVATION,
    "L_Ap_Sid_Time": EphemerisQuantity.LOCAL_APPARENT_SIDEREAL_TIME,
    "L_Ap_SOL_Time": EphemerisQuantity.LOCAL_APPARENT_SOLAR_TIME,
    "r-L_Ap_Hour_Ang": EphemerisQuantity.LOCAL_APPARENT_HOUR_ANGLE,
}

RequestQuantityForQuantity: dict[
    EphemerisQuantity, Optional[HorizonsRequestObserverQuantities]
] = {
    EphemerisQuantity.BODY: None,
    EphemerisQuantity.JULIAN_DATE: None,
    EphemerisQuantity.DATE_TIME: None,
    EphemerisQuantity.RIGHT_ASCENSION: HorizonsRequestObserverQuantities.ASTROMETRIC_RA_DEC,
    EphemerisQuantity.DECLINATION: HorizonsRequestObserverQuantities.ASTROMETRIC_RA_DEC,
    EphemerisQuantity.ECLIPTIC_LONGITUDE: HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT,
    EphemerisQuantity.ECLIPTIC_LATITUDE: HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT,
    EphemerisQuantity.APPARENT_MAGNITUDE: HorizonsRequestObserverQuantities.VISUAL_MAGNITUDE_SURFACE_BRIGHTNESS,
    EphemerisQuantity.SURFACE_BRIGHTNESS: HorizonsRequestObserverQuantities.VISUAL_MAGNITUDE_SURFACE_BRIGHTNESS,
    EphemerisQuantity.ILLUMINATION: HorizonsRequestObserverQuantities.ILLUMINATED_FRACTION,
    EphemerisQuantity.OBSERVER_SUB_LON: HorizonsRequestObserverQuantities.OBSERVER_SUB_LONG_LAT,
    EphemerisQuantity.OBSERVER_SUB_LAT: HorizonsRequestObserverQuantities.OBSERVER_SUB_LONG_LAT,
    EphemerisQuantity.SUN_SUB_LON: HorizonsRequestObserverQuantities.SOLAR_SUB_LONG_LAT,
    EphemerisQuantity.SUN_SUB_LAT: HorizonsRequestObserverQuantities.SOLAR_SUB_LONG_LAT,
    EphemerisQuantity.SOLAR_NORTH_ANGLE: HorizonsRequestObserverQuantities.SUB_SOLAR_POS_ANGLE_DISTANCE,
    EphemerisQuantity.SOLAR_NORTH_DISTANCE: HorizonsRequestObserverQuantities.SUB_SOLAR_POS_ANGLE_DISTANCE,
    EphemerisQuantity.NORTH_POLE_ANGLE: HorizonsRequestObserverQuantities.NORTH_POLE_POS_ANGLE_DISTANCE,
    EphemerisQuantity.NORTH_POLE_DISTANCE: HorizonsRequestObserverQuantities.NORTH_POLE_POS_ANGLE_DISTANCE,
    EphemerisQuantity.DELTA: HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE,
    EphemerisQuantity.DELTA_DOT: HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE,
    EphemerisQuantity.PHASE_ANGLE: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LON: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LAT: HorizonsRequestObserverQuantities.PHASE_ANGLE_BISECTOR,
}

OrbitalElementsQuantityForColumnName = {
    "body": OrbitalElementsQuantity.BODY,
    "EC": OrbitalElementsQuantity.ECCENTRICITY,
    "QR": OrbitalElementsQuantity.PERIAPSIS_DISTANCE,
    "IN": OrbitalElementsQuantity.INCLINATION,
    "OM": OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE,
    "W": OrbitalElementsQuantity.ARGUMENT_OF_PERIFOCUS,
    "Tp": OrbitalElementsQuantity.PERIAPSIS_TIME,
    "N": OrbitalElementsQuantity.MEAN_MOTION,
    "MA": OrbitalElementsQuantity.MEAN_ANOMALY,
    "TA": OrbitalElementsQuantity.TRUE_ANOMALY,
    "A": OrbitalElementsQuantity.SEMI_MAJOR_AXIS,
    "AD": OrbitalElementsQuantity.APOAPSIS_DISTANCE,
    "PR": OrbitalElementsQuantity.ORBITAL_PERIOD,
}

ANGLE_QUANTITIES = {
    EphemerisQuantity.RIGHT_ASCENSION,
    EphemerisQuantity.DECLINATION,
    EphemerisQuantity.ECLIPTIC_LONGITUDE,
    EphemerisQuantity.ECLIPTIC_LATITUDE,
    EphemerisQuantity.OBSERVER_SUB_LON,
    EphemerisQuantity.OBSERVER_SUB_LAT,
    EphemerisQuantity.SUN_SUB_LON,
    EphemerisQuantity.SUN_SUB_LAT,
    EphemerisQuantity.SOLAR_NORTH_ANGLE,
    EphemerisQuantity.NORTH_POLE_ANGLE,
    EphemerisQuantity.PHASE_ANGLE,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LON,
    EphemerisQuantity.PHASE_ANGLE_BISECTOR_LAT,
}

ANGLE_QUANTITIES.update(
    {
        OrbitalElementsQuantity.INCLINATION,
        OrbitalElementsQuantity.ASCENDING_NODE_LONGITUDE,
        OrbitalElementsQuantity.ARGUMENT_OF_PERIFOCUS,
        OrbitalElementsQuantity.MEAN_ANOMALY,
        OrbitalElementsQuantity.TRUE_ANOMALY,
    }
)
