from pwdlib import PasswordHash
from sqlalchemy import select

from app.models import MedicationSchedule, Patient, SimulationState, User


DEMO_USERS = (
    ("caregiver-a@example.test", "Người thân A", "caregiver"),
    ("caregiver-b@example.test", "Người thân B", "caregiver"),
    ("operator@example.test", "Điều khiển mô phỏng", "operator"),
)


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
                ("Thuốc A", 1, "08:00"),
                ("Thuốc B", 2, "12:00"),
                ("Thuốc C", 3, "20:00"),
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
                    medication_name="Thuốc mẫu B",
                    slot=2,
                    time="09:00",
                    active=True,
                )
            )

        if db.scalar(select(SimulationState.id).where(SimulationState.device_id == "SIM-001")) is None:
            db.add(
                SimulationState(
                    device_id="SIM-001",
                    virtual_clock="2026-10-09T07:59:00+07:00",
                    compartments=[
                        {"slot": 1, "medication_name": "Thuốc A", "pill_count": 10, "weight_grams": 5.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ"},
                        {"slot": 2, "medication_name": "Thuốc B", "pill_count": 8, "weight_grams": 4.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ"},
                        {"slot": 3, "medication_name": "Thuốc C", "pill_count": 12, "weight_grams": 6.0, "lid_open": False, "led": "Tắt", "reminder": "Chưa đến giờ"},
                    ],
                )
            )
