from enum import Enum
import re


class Quantity(Enum):
    """
    Combined enum for all astronomical quantities, including both ephemeris columns and orbital elements.
    Names are SQL-friendly.
    """

    # Basic identifiers
    BODY = "body"
    JULIAN_DATE = "julian_date"
    JULIAN_DATE_FRACTION = "julian_date_fraction"
    DATE_TIME = "date_time"

    # Positional quantities
    RIGHT_ASCENSION = "right_ascension"
    DECLINATION = "declination"
    ECLIPTIC_LONGITUDE = "ecliptic_longitude"
    ECLIPTIC_LATITUDE = "ecliptic_latitude"
    APPARENT_AZIMUTH = "apparent_azimuth"
    APPARENT_ELEVATION = "apparent_elevation"
    HELIOCENTRIC_ECLIPTIC_LONGITUDE = "heliocentric_ecliptic_longitude"

    # Magnitude and brightness
    APPARENT_MAGNITUDE = "apparent_magnitude"
    SURFACE_BRIGHTNESS = "surface_brightness"
    ILLUMINATION = "illumination"

    # Sub-observer and sub-solar points
    OBSERVER_SUB_LON = "observer_sub_lon"
    OBSERVER_SUB_LAT = "observer_sub_lat"
    SUN_SUB_LON = "sun_sub_lon"
    SUN_SUB_LAT = "sun_sub_lat"

    # Angles and distances
    SOLAR_NORTH_ANGLE = "solar_north_angle"
    SOLAR_NORTH_DISTANCE = "solar_north_distance"
    NORTH_POLE_ANGLE = "north_pole_angle"
    NORTH_POLE_DISTANCE = "north_pole_distance"
    DELTA = "delta"
    DELTA_DOT = "delta_dot"
    PHASE_ANGLE = "phase_angle"
    PHASE_ANGLE_BISECTOR_LON = "phase_angle_bisector_lon"
    PHASE_ANGLE_BISECTOR_LAT = "phase_angle_bisector_lat"
    ELONGATION = "elongation"

    # Time-related
    LOCAL_APPARENT_SIDEREAL_TIME = "local_apparent_sidereal_time"
    LOCAL_APPARENT_SOLAR_TIME = "local_apparent_solar_time"
    LOCAL_APPARENT_HOUR_ANGLE = "local_apparent_hour_angle"

    # Orbital elements
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

    # Special markers
    SOLAR_PRESENCE_CONDITION_CODE = "solar_presence_condition_code"
    TARGET_EVENT_MARKER = "target_event_marker"


def normalize_column_name(key: str) -> str:
    return re.sub(r"_+", "_", key.strip())


# Set of quantities that represent angles (in degrees)
ANGLE_QUANTITIES = {
    Quantity.RIGHT_ASCENSION,
    Quantity.DECLINATION,
    Quantity.ECLIPTIC_LONGITUDE,
    Quantity.ECLIPTIC_LATITUDE,
    Quantity.OBSERVER_SUB_LON,
    Quantity.OBSERVER_SUB_LAT,
    Quantity.SUN_SUB_LON,
    Quantity.SUN_SUB_LAT,
    Quantity.SOLAR_NORTH_ANGLE,
    Quantity.NORTH_POLE_ANGLE,
    Quantity.PHASE_ANGLE,
    Quantity.PHASE_ANGLE_BISECTOR_LON,
    Quantity.PHASE_ANGLE_BISECTOR_LAT,
    Quantity.INCLINATION,
    Quantity.ASCENDING_NODE_LONGITUDE,
    Quantity.ARGUMENT_OF_PERIFOCUS,
    Quantity.MEAN_ANOMALY,
    Quantity.TRUE_ANOMALY,
}
