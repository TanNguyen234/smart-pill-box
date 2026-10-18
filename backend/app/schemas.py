from datetime import datetime
import re
from typing import Literal
from uuid import UUID, uuid4

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
    event_uuid: UUID = Field(default_factory=uuid4)
    slot: int | None = Field(default=None, ge=1, le=3)
    compartment_id: int | None = Field(default=None, ge=1, le=3)
    event_type: Literal[
        "LID_OPENED",
        "LID_CLOSED",
        "WEIGHT_READING",
        "WEIGHT_SAMPLE",
        "WEIGHT_CHANGED",
        "CONFIRM_PRESSED",
        "CONFIRMED",
        "PILL_REMOVED",
        "PILL_DISPENSED",
        "DOSE_CONFIRMED",
    ]
    payload: dict | None = None
    weight_g: float | None = None
    occurrence_id: int | None = None

    @property
    def resolved_slot(self) -> int:
        target = self.compartment_id if self.compartment_id is not None else self.slot
        if target is None:
            raise ValueError("Cần cung cấp slot hoặc compartment_id")
        return target

    @property
    def resolved_weight_g(self) -> float | None:
        if self.weight_g is not None:
            return float(self.weight_g)
        if isinstance(self.payload, dict):
            if "weight_g" in self.payload:
                return float(self.payload["weight_g"])
            if "weight_grams" in self.payload:
                return float(self.payload["weight_grams"])
        return None

    @property
    def resolved_occurrence_id(self) -> int | None:
        if self.occurrence_id is not None:
            return int(self.occurrence_id)
        if isinstance(self.payload, dict) and "occurrence_id" in self.payload:
            return int(self.payload["occurrence_id"])
        return None


class ClockAdvanceInput(BaseModel):
    event_uuid: UUID = Field(default_factory=uuid4)
    minutes: int = Field(default=1, ge=1, le=60)



class SimulationResetInput(BaseModel):
    confirm: bool = False
    confirmation: str | None = None
    event_uuid: UUID = Field(default_factory=uuid4)


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



class ClockModeInput(BaseModel):
    clock_mode: Literal["SIMULATION", "REALTIME"]
