from datetime import datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginInput(BaseModel):
    email: str
    password: str


class UserOutput(BaseModel):
    id: int
    email: str
    display_name: str
    role: Literal["caregiver", "operator"]

    model_config = ConfigDict(from_attributes=True)


class PatientOutput(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleCreate(BaseModel):
    patient_id: int = Field(gt=0)
    medication_name: str = Field(min_length=1, max_length=100)
    slot: int = Field(ge=1, le=3)
    time: str
    active: bool = True

    @field_validator("medication_name")
    @classmethod
    def clean_medication_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tên thuốc không được để trống")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Giờ phải theo định dạng HH:mm")
        return value


class SchedulePatch(BaseModel):
    medication_name: str | None = Field(default=None, min_length=1, max_length=100)
    slot: int | None = Field(default=None, ge=1, le=3)
    time: str | None = None
    active: bool | None = None

    @field_validator("medication_name")
    @classmethod
    def clean_medication_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Tên thuốc không được để trống")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Giờ phải theo định dạng HH:mm")
        return value


class EventInput(BaseModel):
    event_uuid: UUID
    slot: int | None = Field(default=None, ge=1, le=3)
    event_type: Literal[
        "LID_OPENED",
        "LID_CLOSED",
        "PILL_REMOVED",
        "CONFIRM_PRESSED",
        "CONFIRMED",
        "WEIGHT_CHANGED",
        "WEIGHT_SAMPLE",
    ]
    weight_grams: float | None = None


class ClockAdvanceInput(BaseModel):
    minutes: int = Field(gt=0, le=1440)


class SimulationResetInput(BaseModel):
    confirmation: str = Field(default="RESET_DEMO")


class AlertOutput(BaseModel):
    id: int
    patient_id: int
    occurrence_id: int | None = None
    recipient_id: int | None = None
    kind: str
    status: str = "PENDING"
    message: str
    note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertResolveInput(BaseModel):
    note: str | None = None


class AlertPatchInput(BaseModel):
    status: Literal["PENDING", "CHECKED", "ASSISTED", "IGNORED"] | None = None
    note: str | None = None


class DoseOutput(BaseModel):
    id: int
    schedule_id: int
    scheduled_at: datetime
    deadline_at: datetime | None = None
    confirmed_at: datetime | None = None
    status: str
    reminder_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DeviceEventOutput(BaseModel):
    id: int
    event_uuid: str
    event_type: str
    patient_id: int | None = None
    slot: int | None = None
    occurrence_id: int | None = None
    payload: dict
    occurred_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
