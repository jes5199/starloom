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


class HorizonsSolarEphemerisRow(Base):
    """
    This represents values that are specifically about the Sun as seen from a specific location.
    """

    __tablename__ = "solar_ephemeris"
    julian_date = Column(Integer, nullable=False)
    julian_date_fraction = Column(Float, nullable=False)
    date_time = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)

    solar_presence_condition_code = Column(String)  # */C/N/A/' '
    target_event_marker = Column(String)  # r/e/t/s

    azimuth = Column(Float)
    elevation = Column(Float)

    local_apparent_sidereal_time = Column(Float)
    local_apparent_solar_time = Column(Float)
    local_apparent_hour_angle = Column(Float)

    created_on = Column(DateTime, server_default=func.now(), nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint(
            "latitude", "longitude", "altitude", "julian_date", "julian_date_fraction"
        ),
    )
