"""
Pydantic schemas for the Medication Management App.

Provides request/response validation models for the API layer.
Each entity follows a Base → Create → Response pattern:

- **Base**:     Shared fields used in both creation and reading.
- **Create**:   Fields required when creating a new record (extends Base).
- **Response**:  Fields returned by the API, including the DB-generated id
                 and any nested relationships (extends Base, enables ORM mode).
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums  (mirror the SQLAlchemy enums for use in the Pydantic layer)
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """Allowed roles for a user within a family."""
    patient = "patient"
    caregiver = "caregiver"


class AdherenceStatus(str, Enum):
    """Possible states for an adherence log entry."""
    pending = "pending"
    taken = "taken"
    missed = "missed"


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  Schedule Schemas                                                      ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class ScheduleBase(BaseModel):
    """Shared fields for a dosing schedule."""
    time_slot: time = Field(..., description="Time of day for the dose (HH:MM:SS)")
    repeat_days: str = Field(
        ...,
        description="Comma-separated day codes, e.g. 'Mon,Wed,Fri' or 'daily'",
    )


class ScheduleCreate(ScheduleBase):
    """Fields required when creating a new schedule."""
    medication_id: int


class ScheduleResponse(ScheduleBase):
    """Schedule data returned by the API."""
    id: int
    medication_id: int

    model_config = ConfigDict(from_attributes=True)


class MedicationSummary(BaseModel):
    """Lightweight medication info embedded in dashboard responses."""
    id: int
    name: str
    dosage_mg: float

    model_config = ConfigDict(from_attributes=True)


class DashboardScheduleResponse(BaseModel):
    """A single scheduled dose for the dashboard, with medication and status."""
    schedule_id: int = Field(..., description="Schedule primary key")
    time_slot: time = Field(..., description="Scheduled time of day")
    repeat_days: str = Field(..., description="Days this schedule repeats on")
    medication: MedicationSummary = Field(..., description="Medication details")
    adherence_status: AdherenceStatus = Field(
        AdherenceStatus.pending,
        description="Current adherence status for today",
    )
    adherence_log_id: Optional[int] = Field(
        None, description="ID of today's adherence log entry, if one exists",
    )


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  Medication Schemas                                                    ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class MedicationBase(BaseModel):
    """Shared fields for a medication entry."""
    name: str = Field(..., min_length=1, description="Medication name")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")
    batch_number: Optional[str] = Field(None, description="Manufacturer batch/lot number")
    dosage_mg: float = Field(..., gt=0, description="Dosage strength in milligrams")
    stock_quantity: int = Field(0, ge=0, description="Current stock count")
    expiry_date: Optional[date] = Field(None, description="Expiration date")


class MedicationCreate(MedicationBase):
    """Fields required when creating a new medication."""
    user_id: int


class MedicationResponse(MedicationBase):
    """Medication data returned by the API, including nested schedules."""
    id: int
    user_id: int
    schedules: list[ScheduleResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    """Shared fields for a user account."""
    name: str = Field(..., min_length=1, description="Full name")
    email: str = Field(..., description="Unique email address")
    role: UserRole = Field(UserRole.patient, description="User role within the family")
    designation: Optional[str] = Field("Member", description="Relationship/designation (e.g. Father, Mother)")
    member_code: Optional[str] = Field("A", description="Short 1-2 char family code (e.g. A, B)")


class UserCreate(UserBase):
    """Fields required when creating a new user."""
    family_id: int
    password: str = Field(
        ...,
        min_length=1,
        description="Plain-text password",
    )


class FamilyMemberCreate(BaseModel):
    """Fields required when adding a family member to an existing household."""
    name: str = Field(..., min_length=1)
    designation: str = Field(..., description="Father, Mother, Son, Daughter, Caregiver, etc.")
    member_code: str = Field(..., max_length=2, description="Short code e.g. A, B, C")
    role: UserRole = UserRole.patient


class UserResponse(UserBase):
    """
    User data returned by the API.
    """
    id: int
    family_id: int
    medications: list[MedicationResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Health Document Schemas
# ---------------------------------------------------------------------------

class HealthDocumentBase(BaseModel):
    """Shared fields for a prescription or health document."""
    title: str = Field(..., min_length=1, description="Document title")
    document_type: str = Field("Prescription", description="Prescription, Health Report, Lab Report, etc.")
    file_name: str
    mime_type: str


class HealthDocumentCreate(HealthDocumentBase):
    """Fields required when uploading a new document."""
    family_id: int
    user_id: int
    file_data: str  # Base64 string


class HealthDocumentResponse(HealthDocumentBase):
    """Document metadata and content returned by the API."""
    id: int
    family_id: int
    user_id: int
    file_data: str
    upload_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  Family Schemas                                                        ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class FamilyBase(BaseModel):
    """Shared fields for a family group."""
    name: str = Field(..., min_length=1, description="Family display name")


class FamilyCreate(FamilyBase):
    """Fields required when creating a new family (join_code is auto-generated)."""
    pass


class FamilyResponse(FamilyBase):
    """Family data returned by the API, including nested users."""
    id: int
    join_code: str
    users: list[UserResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  Adherence Log Schemas                                                 ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class AdherenceLogBase(BaseModel):
    """Shared fields for an adherence record."""
    scheduled_date: date = Field(..., description="Calendar date for this dose")
    status: AdherenceStatus = Field(
        AdherenceStatus.pending,
        description="Current adherence status",
    )


class AdherenceLogCreate(AdherenceLogBase):
    """Fields required when creating a new adherence log entry."""
    schedule_id: int


class AdherenceLogResponse(AdherenceLogBase):
    """Adherence log data returned by the API."""
    id: int
    schedule_id: int
    logged_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  Caregiver Alert Schemas                                               ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class CaregiverAlertResponse(BaseModel):
    """A single caregiver alert triggered by a missed dose."""
    caregiver_name: str = Field(..., description="Name of the caregiver being notified")
    patient_name: str = Field(..., description="Name of the patient who missed a dose")
    medication_name: str = Field(..., description="Name of the missed medication")
    scheduled_time: time = Field(..., description="Time the dose was originally scheduled")
    message: str = Field(..., description="Human-readable alert message")

