from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ConfigBase:
    from_attributes = True
    orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str

class ScheduleBase(BaseModel):
    care_receiver_id: int
    compartment: int
    time: str
    medication_name: str

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
    id: int
    is_active: bool
    class Config(ConfigBase):
        pass

class EventResponse(BaseModel):
    id: int
    schedule_id: int
    timestamp: datetime
    status: str
    compartment: int
    class Config(ConfigBase):
        pass

class AlertResponse(BaseModel):
    id: int
    care_receiver_id: int
    timestamp: datetime
    message: str
    status: str
    class Config(ConfigBase):
        pass

class AlertUpdate(BaseModel):
    status: str
