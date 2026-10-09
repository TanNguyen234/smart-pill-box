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
            raise ValueError("TÃƒÂªn thuÃ¡Â»â€˜c khÃƒÂ´ng Ã„â€˜Ã†Â°Ã¡Â»Â£c Ã„â€˜Ã¡Â»Æ’ trÃ¡Â»â€˜ng")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("GiÃ¡Â»Â phÃ¡ÂºÂ£i theo Ã„â€˜Ã¡Â»â€¹nh dÃ¡ÂºÂ¡ng HH:mm")
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
            raise ValueError("TÃƒÂªn thuÃ¡Â»â€˜c khÃƒÂ´ng Ã„â€˜Ã†Â°Ã¡Â»Â£c Ã„â€˜Ã¡Â»Æ’ trÃ¡Â»â€˜ng")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("GiÃ¡Â»Â phÃ¡ÂºÂ£i theo Ã„â€˜Ã¡Â»â€¹nh dÃ¡ÂºÂ¡ng HH:mm")
        return value


class EventInput(BaseModel):
    event_uuid: UUID
    slot: int = Field(ge=1, le=3)
    event_type: Literal["LID_OPENED", "LID_CLOSED", "WEIGHT_CHANGED", "CONFIRMED"]
    weight_grams: float | None = None

class ClockAdvanceInput(BaseModel):
    minutes: int = Field(gt=0, le=1440)





class AlertOutput(BaseModel):
    id: int
    patient_id: int
    occurrence_id: int | None = None
    kind: str
    message: str
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class AlertResolveInput(BaseModel):
    note: str | None = None

