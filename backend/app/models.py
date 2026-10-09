from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(20), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    caregiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    demo: Mapped[bool] = mapped_column(Boolean, default=True)


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    medication_name: Mapped[str] = mapped_column(String(100))
    slot: Mapped[int] = mapped_column(Integer)
    time: Mapped[str] = mapped_column(String(5))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DoseOccurrence(Base):
    __tablename__ = "dose_occurrences"
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("medication_schedules.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")


class DeviceEvent(Base):
    __tablename__ = "device_events"
    __table_args__ = (UniqueConstraint("event_uuid", name="uq_device_event_uuid"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_uuid: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    occurrence_id: Mapped[int | None] = mapped_column(ForeignKey("dose_occurrences.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    occurrence_id: Mapped[int | None] = mapped_column(ForeignKey("dose_occurrences.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulationState(Base):
    __tablename__ = "simulation_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(30), unique=True)
    virtual_clock: Mapped[str] = mapped_column(String(40))
    compartments: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
