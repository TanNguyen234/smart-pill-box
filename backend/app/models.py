from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'caregiver', 'operator'

class CareReceiver(Base):
    __tablename__ = "care_receivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    caregiver_id = Column(Integer, ForeignKey("users.id"))
    caregiver = relationship("User")

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    care_receiver_id = Column(Integer, ForeignKey("care_receivers.id"))
    compartment = Column(Integer) # 1, 2, 3
    time = Column(String) # "HH:MM"
    medication_name = Column(String)
    is_active = Column(Boolean, default=True)

class MedicationEvent(Base):
    __tablename__ = "medication_events"
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String) # "opened", "taken", "missed"
    compartment = Column(Integer)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    care_receiver_id = Column(Integer, ForeignKey("care_receivers.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(String)
    status = Column(String, default="pending") # "pending", "checked", "assisted", "ignored"
