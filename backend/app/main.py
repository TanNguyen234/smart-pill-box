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
from app.models import DeviceEvent, MedicationSchedule, Patient, SimulationState, User
from app.schemas import EventInput, LoginInput, PatientOutput, ScheduleCreate, SchedulePatch, UserOutput


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
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    try:
        claims = jwt.decode(credentials.credentials, request.app.state.jwt_secret, algorithms=["HS256"])
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Mã truy cập không hợp lệ hoặc đã hết hạn")
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Tài khoản không hoạt động")
    return user


def require_role(role: str):
    def dependency(user: User = Depends(require_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail="Không có quyền thực hiện thao tác này")
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
        raise RuntimeError("Thiếu JWT_SECRET. Hãy tạo backend/.env từ .env.example.")
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
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
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
            raise HTTPException(status_code=403, detail="Hồ sơ không thuộc tài khoản này")
        row = MedicationSchedule(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return schedule_json(row)

    @app.patch("/api/schedules/{schedule_id}")
    def update_schedule(schedule_id: int, payload: SchedulePatch, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        row = db.get(MedicationSchedule, schedule_id)
        if row is None or db.scalar(select(Patient.id).where(Patient.id == row.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy lịch")
        changes = payload.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(status_code=422, detail="Cần ít nhất một giá trị cập nhật hợp lệ")
        for key, value in changes.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return schedule_json(row)

    @app.get("/api/simulation/state")
    def simulation_state(user: User = Depends(operator_only), db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        return state_json(db, state)

    @app.post("/api/simulation/events")
    def simulation_event(payload: EventInput, user: User = Depends(operator_only), db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            same_content = existing.event_type == payload.event_type and existing.payload.get("slot") == payload.slot
            if not same_content:
                raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
            return state_json(db, state, idempotent=True)

        compartments = [dict(item) for item in state.compartments]
        compartment = next(item for item in compartments if item["slot"] == payload.slot)
        new_open = payload.event_type == "LID_OPENED"
        if compartment["lid_open"] == new_open:
            action = "đã mở" if new_open else "đã đóng"
            raise HTTPException(status_code=409, detail=f"Nắp ngăn {payload.slot} {action}")
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

    return app


app = create_app()
