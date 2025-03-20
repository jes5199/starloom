from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Float,
    String,
    PrimaryKeyConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class HorizonsOrbitalElementsRow(Base):
    """
    This represents orbital elements for a body.
    """

    __tablename__ = "horizons_orbital_elements"

    # Primary key columns
    body = Column(String, nullable=False)
    julian_date = Column(Integer, nullable=False)
    julian_date_fraction = Column(Float, nullable=False)

    # Orbital elements
    eccentricity = Column(Float)
    periapsis_distance = Column(Float)
    inclination = Column(Float)
    ascending_node_longitude = Column(Float)
    argument_of_perifocus = Column(Float)
    periapsis_time = Column(Float)
    mean_motion = Column(Float)
    mean_anomaly = Column(Float)
    true_anomaly = Column(Float)
    semi_major_axis = Column(Float)
    apoapsis_distance = Column(Float)
    orbital_period = Column(Float)

    # Metadata
    created_on = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("body", "julian_date", "julian_date_fraction"),
    )
