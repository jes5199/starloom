from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Float,
    String,
    PrimaryKeyConstraint,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class HorizonsGlobalEphemerisRow(Base):
    """
    This represents values that are the same for all observers.
    """

    __tablename__ = "horizons_ephemeris"
    body = Column(String, nullable=False)
    julian_date = Column(Integer, nullable=False)
    julian_date_fraction = Column(Float, nullable=False)
    date_time = Column(String, nullable=False)
    right_ascension = Column(Float)
    declination = Column(Float)
    ecliptic_longitude = Column(Float)
    ecliptic_latitude = Column(Float)
    apparent_magnitude = Column(Float)
    surface_brightness = Column(Float)
    illumination = Column(Float)
    observer_sub_lon = Column(Float)
    observer_sub_lat = Column(Float)
    sun_sub_lon = Column(Float)
    sun_sub_lat = Column(Float)
    solar_north_angle = Column(Float)
    solar_north_distance = Column(Float)
    north_pole_angle = Column(Float)
    north_pole_distance = Column(Float)
    delta = Column(Float)
    delta_dot = Column(Float)
    phase_angle = Column(Float)
    phase_angle_bisector_lon = Column(Float)
    phase_angle_bisector_lat = Column(Float)
    created_on = Column(DateTime, server_default=func.now(), nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint("body", "julian_date", "julian_date_fraction"),
    )
