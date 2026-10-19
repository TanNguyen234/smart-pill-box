from pwdlib import PasswordHash
from sqlalchemy import select

from app.models import MedicationSchedule, Patient, SimulationState, User


DEMO_USERS = (
    ("caregiver-a@example.test", "Người thân A", "caregiver"),
    ("caregiver-b@example.test", "Người thân B", "caregiver"),
    ("operator@example.test", "Điều khiển mô phỏng", "operator"),
)

DEFAULT_SIMULATION_CLOCK = "2026-10-09T07:59:00+07:00"


def default_compartments() -> list[dict]:
    return [
        {"slot": 1, "medication_name": "Bịch thuốc cữ sáng", "pill_count": 10, "weight_grams": 5.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ", "dose_taken": False},
        {"slot": 2, "medication_name": "Bịch thuốc cữ trưa", "pill_count": 8, "weight_grams": 4.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ", "dose_taken": False},
        {"slot": 3, "medication_name": "Bịch thuốc cữ tối", "pill_count": 12, "weight_grams": 6.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ", "dose_taken": False},
    ]


def seed_demo(session_factory, demo_password: str) -> None:
    password_hash = PasswordHash.recommended()
    with session_factory.begin() as db:
        users = {}
        for email, name, role in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    display_name=name,
                    role=role,
                    password_hash=password_hash.hash(demo_password),
                )
                db.add(user)
                db.flush()
            else:
                user.password_hash = password_hash.hash(demo_password)
                user.display_name = name
                user.role = role
                user.active = True
            users[email] = user

        patients = {}
        for email, name in (
            ("caregiver-a@example.test", "Hồ sơ giả A"),
            ("caregiver-b@example.test", "Hồ sơ giả B"),
        ):
            caregiver = users[email]
            patient = db.scalar(select(Patient).where(Patient.caregiver_id == caregiver.id))
            if patient is None:
                patient = Patient(caregiver_id=caregiver.id, name=name, demo=True)
                db.add(patient)
                db.flush()
            patients[email] = patient

        if not db.scalar(select(MedicationSchedule.id).limit(1)):
            for name, slot, schedule_time in (
                ("Bịch thuốc cữ sáng", 1, "08:00"),
                ("Bịch thuốc cữ trưa", 2, "12:00"),
                ("Bịch thuốc cữ tối", 3, "20:00"),
            ):
                db.add(
                    MedicationSchedule(
                        patient_id=patients["caregiver-a@example.test"].id,
                        medication_name=name,
                        slot=slot,
                        time=schedule_time,
                        active=True,
                    )
                )
            db.add(
                MedicationSchedule(
                    patient_id=patients["caregiver-b@example.test"].id,
                    medication_name="Bịch thuốc cữ sáng",
                    slot=2,
                    time="09:00",
                    active=True,
                )
            )

        if db.scalar(select(SimulationState.id).where(SimulationState.device_id == "SIM-001")) is None:
            db.add(
                SimulationState(
                    device_id="SIM-001",
                    patient_id=patients["caregiver-a@example.test"].id,
                    virtual_clock=DEFAULT_SIMULATION_CLOCK,
                    simulation_clock=DEFAULT_SIMULATION_CLOCK,
                    clock_mode="SIMULATION",
                    compartments=default_compartments(),
                )
            )

