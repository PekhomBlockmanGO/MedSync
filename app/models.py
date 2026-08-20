"""
SQLAlchemy ORM models for the Medication Management App.

Defines the database schema for families, users, medications,
schedules, and adherence tracking.
"""

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    """Allowed roles for a user within a family."""
    patient = "patient"
    caregiver = "caregiver"


class AdherenceStatus(str, enum.Enum):
    """Possible states for a single dose adherence record."""
    pending = "pending"
    taken = "taken"
    missed = "missed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Family(Base):
    """
    A family group that multiple users can belong to.

    Attributes:
        id:        Primary key.
        name:      Display name of the family.
        join_code: Unique invite code used to join this family.
    """
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    join_code = Column(String, unique=True, nullable=False, index=True)

    # Relationships
    users = relationship("User", back_populates="family")

    def __repr__(self) -> str:
        return f"<Family id={self.id} name={self.name!r}>"


class User(Base):
    """
    An individual user / family member account linked to a family.

    Attributes:
        id:            Primary key.
        family_id:     FK → families.id.
        role:          'patient' or 'caregiver'.
        name:          Full name.
        email:         Unique email address.
        password_hash: Hashed password.
        designation:   Role/relationship in family (e.g., Father, Mother, Son).
        member_code:   Short 1-2 letter personal code (e.g. A, B, C).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    designation = Column(String, nullable=False, default="Member")
    member_code = Column(String, nullable=False, default="A")

    # Relationships
    family = relationship("Family", back_populates="users")
    medications = relationship("Medication", back_populates="user")
    health_documents = relationship("HealthDocument", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} designation={self.designation!r} code={self.member_code!r}>"


class Medication(Base):
    """
    A medication entry belonging to a shared family stock inventory.

    Attributes:
        id:             Primary key.
        family_id:      FK → families.id (Shared Household Stock).
        user_id:        FK → users.id (Optional creator/owner).
        name:           Medication name.
        gtin:           Global Trade Item Number (barcode identifier).
        batch_number:   Manufacturer batch / lot number.
        dosage_mg:      Dosage strength in milligrams.
        stock_quantity: Current stock count (e.g. tablets remaining).
        expiry_date:    Expiration date of the medication.
    """
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    gtin = Column(String, nullable=True)
    batch_number = Column(String, nullable=True)
    dosage_mg = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=True)

    # Relationships
    user = relationship("User", back_populates="medications")
    schedules = relationship("Schedule", back_populates="medication")

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name!r} dosage={self.dosage_mg}mg>"


class Schedule(Base):
    """
    A recurring dosing schedule tied to a medication and assigned to a family member.

    Attributes:
        id:             Primary key.
        medication_id:  FK → medications.id (Shared Stock item).
        time_slot:      Time of day the dose should be taken.
        repeat_days:    Comma-separated day codes, e.g. "Mon,Wed,Fri"
                        or "daily" for every day.
    """
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    time_slot = Column(Time, nullable=False)
    repeat_days = Column(String, nullable=False)

    # Relationships
    medication = relationship("Medication", back_populates="schedules")
    adherence_logs = relationship("AdherenceLog", back_populates="schedule")

    def __repr__(self) -> str:
        return f"<Schedule id={self.id} time={self.time_slot} days={self.repeat_days!r}>"


class AdherenceLog(Base):
    """
    Tracks whether a scheduled dose was taken, missed, or is still pending.

    Attributes:
        id:              Primary key.
        schedule_id:     FK → schedules.id.
        scheduled_date:  The calendar date for this dose.
        status:          'pending', 'taken', or 'missed'.
        logged_at:       Timestamp when the status was last recorded.
    """
    __tablename__ = "adherence_logs"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(
        Enum(AdherenceStatus),
        nullable=False,
        default=AdherenceStatus.pending,
    )
    logged_at = Column(DateTime, server_default=func.now())

    # Relationships
    schedule = relationship("Schedule", back_populates="adherence_logs")

    def __repr__(self) -> str:
        return (
            f"<AdherenceLog id={self.id} date={self.scheduled_date} "
            f"status={self.status}>"
        )


class HealthDocument(Base):
    """
    Digitally stored medical document (prescription, report) for a family member.
    """
    __tablename__ = "health_documents"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    document_type = Column(String, nullable=False, default="Prescription")
    file_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    file_data = Column(String, nullable=False)  # Base64 data string
    upload_date = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="health_documents")
    family = relationship("Family")

    def __repr__(self) -> str:
        return f"<HealthDocument id={self.id} title={self.title!r} type={self.document_type}>"

