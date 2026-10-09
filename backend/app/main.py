import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, make_engine, make_session_factory
from app.models import DeviceEvent, MedicationSchedule, Patient, SimulationState, User, DoseOccurrence, Alert
from app.schemas import EventInput, LoginInput, PatientOutput, ScheduleCreate, SchedulePatch, UserOutput, ClockAdvanceInput, AlertOutput, AlertResolveInput


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")
password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Cáº§n Ä‘Äƒng nháº­p")
    try:
        claims = jwt.decode(credentials.credentials, request.app.state.jwt_secret, algorithms=["HS256"])
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="MÃ£ truy cáº­p khÃ´ng há»£p lá»‡ hoáº·c Ä‘Ã£ háº¿t háº¡n")
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="TÃ i khoáº£n khÃ´ng hoáº¡t Ä‘á»™ng")
    return user


def require_role(role: str):
    def dependency(user: User = Depends(require_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail="KhÃ´ng cÃ³ quyá»n thá»±c hiá»‡n thao tÃ¡c nÃ y")
        return user

    return dependency


caregiver_only = require_role("caregiver")
operator_only = require_role("operator")


def schedule_json(schedule: MedicationSchedule) -> dict:
    return {
        "id": schedule.id,
        "patient_id": schedule.patient_id,
        "medication_name": schedule.medication_name,
        "slot": schedule.slot,
        "time": schedule.time,
        "active": schedule.active,
    }


def state_json(db: Session, state: SimulationState, idempotent: bool = False) -> dict:
    active_schedules = db.scalars(
        select(MedicationSchedule).where(MedicationSchedule.active.is_(True)).order_by(MedicationSchedule.time)
    ).all()
    return {
        "device_id": state.device_id,
        "virtual_clock": state.virtual_clock,
        "compartments": state.compartments,
        "active_schedules": [
            {"medication_name": item.medication_name, "slot": item.slot, "time": item.time}
            for item in active_schedules
        ],
        "idempotent": idempotent,
    }


def create_app(database_url: str | None = None, jwt_secret: str | None = None) -> FastAPI:
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///data/smartpill.sqlite3")
    jwt_secret = jwt_secret or os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("Thiáº¿u JWT_SECRET. HÃ£y táº¡o backend/.env tá»« .env.example.")
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.removeprefix("sqlite:///")
        if sqlite_path and sqlite_path != ":memory:":
            path = Path(sqlite_path)
            if not path.is_absolute():
                path = (BACKEND_ROOT / path).resolve()
                database_url = f"sqlite:///{path.as_posix()}"
            path.parent.mkdir(parents=True, exist_ok=True)
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    app = FastAPI(title="Smart Pill Box API", version="0.1.0")
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.jwt_secret = jwt_secret
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "smart-pill-box-api"}

    @app.post("/api/auth/login")
    def login(payload: LoginInput, request: Request, db: Session = Depends(get_db)):
        user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
        if user is None or not user.active or not password_hasher.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email hoáº·c máº­t kháº©u khÃ´ng Ä‘Ãºng")
        expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
        token = jwt.encode(
            {"sub": str(user.id), "exp": expires_at, "iat": datetime.now(timezone.utc)},
            request.app.state.jwt_secret,
            algorithm="HS256",
        )
        return {"access_token": token, "token_type": "bearer", "expires_in": 28800, "user": UserOutput.model_validate(user)}

    @app.get("/api/me", response_model=UserOutput)
    def me(user: User = Depends(require_user)):
        return user

    @app.get("/api/patients", response_model=list[PatientOutput])
    def patients(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        return db.scalars(select(Patient).where(Patient.caregiver_id == user.id).order_by(Patient.id)).all()

    @app.get("/api/schedules")
    def schedules(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        patient_ids = select(Patient.id).where(Patient.caregiver_id == user.id)
        rows = db.scalars(
            select(MedicationSchedule).where(MedicationSchedule.patient_id.in_(patient_ids)).order_by(MedicationSchedule.time)
        ).all()
        return [schedule_json(row) for row in rows]

    @app.post("/api/schedules", status_code=status.HTTP_201_CREATED)
    def create_schedule(payload: ScheduleCreate, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        patient = db.get(Patient, payload.patient_id)
        if patient is None or patient.caregiver_id != user.id:
            raise HTTPException(status_code=403, detail="Há»“ sÆ¡ khÃ´ng thuá»™c tÃ i khoáº£n nÃ y")
        row = MedicationSchedule(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return schedule_json(row)

    @app.patch("/api/schedules/{schedule_id}")
    def update_schedule(schedule_id: int, payload: SchedulePatch, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        row = db.get(MedicationSchedule, schedule_id)
        if row is None or db.scalar(select(Patient.id).where(Patient.id == row.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="KhÃ´ng tÃ¬m tháº¥y lá»‹ch")
        changes = payload.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(status_code=422, detail="Cáº§n Ã­t nháº¥t má»™t giÃ¡ trá»‹ cáº­p nháº­t há»£p lá»‡")
        for key, value in changes.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return schedule_json(row)

    @app.get("/api/simulation/state")
    def simulation_state(user: User = Depends(operator_only), db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="ChÆ°a khá»Ÿi táº¡o há»™p mÃ´ phá»ng")
        return state_json(db, state)

    @app.post("/api/simulation/events")
    def simulation_event(payload: EventInput, user: User = Depends(operator_only), db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="ChÆ°a khá»Ÿi táº¡o há»™p mÃ´ phá»ng")
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            same_content = existing.event_type == payload.event_type and existing.payload.get("slot") == payload.slot
            if not same_content:
                raise HTTPException(status_code=409, detail="event_uuid Ä‘Ã£ Ä‘Æ°á»£c dÃ¹ng cho ná»™i dung khÃ¡c")
            return state_json(db, state, idempotent=True)

        compartments = [dict(item) for item in state.compartments]
        compartment = next(item for item in compartments if item["slot"] == payload.slot)
        new_open = payload.event_type == "LID_OPENED"
        if compartment["lid_open"] == new_open:
            action = "Ä‘Ã£ má»Ÿ" if new_open else "Ä‘Ã£ Ä‘Ã³ng"
            raise HTTPException(status_code=409, detail=f"Náº¯p ngÄƒn {payload.slot} {action}")
        compartment["lid_open"] = new_open
        state.compartments = compartments
        state.updated_at = datetime.now(timezone.utc)
        db.add(
            DeviceEvent(
                event_uuid=event_uuid,
                event_type=payload.event_type,
                occurrence_id=None,
                payload={"device_id": "SIM-001", "slot": payload.slot},
            )
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)

    @app.get("/api/simulation/clock/state")
    def clock_state(db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        return state_json(db, state)

    @app.post("/api/simulation/clock/advance")
    def advance_clock(payload: ClockAdvanceInput, db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        
        try:
            current_time = datetime.fromisoformat(state.virtual_clock)
        except ValueError:
            current_time = datetime.now(timezone.utc)
            
        new_time = current_time + timedelta(minutes=payload.minutes)
        state.virtual_clock = new_time.isoformat()
        state.updated_at = datetime.now(timezone.utc)
        
        passed_milestones = []
        active_schedules = db.scalars(select(MedicationSchedule).where(MedicationSchedule.active.is_(True))).all()
        
        compartments = [dict(c) for c in state.compartments]
        
        # 1. Check for new scheduled occurrences
        for sched in active_schedules:
            hour, minute = map(int, sched.time.split(":"))
            sched_datetime = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if current_time < sched_datetime <= new_time:
                occurrence = DoseOccurrence(
                    schedule_id=sched.id,
                    scheduled_at=sched_datetime,
                    status="pending"
                )
                db.add(occurrence)
                
                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["led"] = "Bật"
                        comp["reminder"] = f"Đến giờ {sched.time}"
                        
                passed_milestones.append({
                    "ngan": sched.slot,
                    "thuoc": sched.medication_name,
                    "thoi_gian_nhac": sched.time,
                    "trang_thai": "Tới giờ uống thuốc, còi và đèn đã bật (Mô phỏng)"
                })

        # 2. Check for overdue occurrences (Task 5)
        db.flush()
        pending_occurrences = db.scalars(select(DoseOccurrence).where(DoseOccurrence.status == "pending")).all()
        
        for occ in pending_occurrences:
            delay = (new_time - occ.scheduled_at).total_seconds() / 60.0
            
            # Sau 2 phút chưa xác nhận -> Nhắc lại
            if delay >= 2 and delay < 5:
                sched = db.get(MedicationSchedule, occ.schedule_id)
                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["reminder"] = f"NHẮC LẠI: Đã trễ {int(delay)} phút!"
            
            # Sau 5 phút chưa xác nhận -> Tạo cảnh báo 1 lần
            if delay >= 5:
                sched = db.get(MedicationSchedule, occ.schedule_id)
                occ.status = "overdue_unconfirmed"
                
                existing_alert = db.scalar(select(Alert).where(Alert.occurrence_id == occ.id))
                if not existing_alert:
                    new_alert = Alert(
                        patient_id=sched.patient_id,
                        occurrence_id=occ.id,
                        kind="QUA_HAN",
                        message=f"Quá hạn 5 phút chưa uống {sched.medication_name} (Ngăn {sched.slot})"
                    )
                    db.add(new_alert)
                    passed_milestones.append({
                        "ngan": sched.slot,
                        "thuoc": sched.medication_name,
                        "thoi_gian_nhac": sched.time,
                        "trang_thai": "Đã tạo cảnh báo quá hạn gửi đến người thân!"
                    })
                
                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["led"] = "Tắt"
                        comp["reminder"] = "Đã quá hạn (Chưa uống)"

        state.compartments = compartments
        
        compartments = [dict(c) for c in state.compartments]
        
        for sched in active_schedules:
            hour, minute = map(int, sched.time.split(":"))
            sched_datetime = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if current_time < sched_datetime <= new_time:
                occurrence = DoseOccurrence(
                    schedule_id=sched.id,
                    scheduled_at=sched_datetime,
                    status="pending"
                )
                db.add(occurrence)
                
                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["led"] = "Bật"
                        comp["reminder"] = f"Đến giờ {sched.time}"
                        
                passed_milestones.append({
                    "ngan": sched.slot,
                    "thuoc": sched.medication_name,
                    "thoi_gian_nhac": sched.time,
                    "trang_thai": "Tới giờ uống thuốc, còi và đèn đã bật (Mô phỏng)"
                })
        
        state.compartments = compartments
        db.commit()
        db.refresh(state)
        
        result = state_json(db, state)
        result["passed_milestones"] = passed_milestones
        return result

    @app.get("/api/alerts", response_model=list[AlertOutput])
    def get_alerts(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        patient_ids = select(Patient.id).where(Patient.caregiver_id == user.id)
        rows = db.scalars(select(Alert).where(Alert.patient_id.in_(patient_ids)).order_by(Alert.created_at.desc())).all()
        return rows

    @app.post("/api/alerts/{alert_id}/resolve", response_model=AlertOutput)
    def resolve_alert(alert_id: int, payload: AlertResolveInput, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        alert = db.get(Alert, alert_id)
        if not alert or db.scalar(select(Patient.id).where(Patient.id == alert.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
        
        alert.resolved_at = datetime.now(timezone.utc)
        if payload.note:
            alert.message += f" (Ghi chú: {payload.note})"
            
        db.commit()
        db.refresh(alert)
        return alert

    return app

app = create_app()
