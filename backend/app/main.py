import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import Base, make_engine, make_session_factory
from app.models import Alert, DeviceEvent, DoseOccurrence, MedicationSchedule, Patient, SimulationState, User
from app.schemas import ClockAdvanceInput, EventInput, LoginInput, PatientOutput, ScheduleCreate, SchedulePatch, SimulationResetInput, UserOutput
from app.seed import DEFAULT_SIMULATION_CLOCK, default_compartments


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
VIETNAM_TZ = timezone(timedelta(hours=7))
ACTIVE_DOSE_STATUSES = ("pending", "reminded", "overdue")


def parse_virtual_clock(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VIETNAM_TZ)
    return parsed.astimezone(VIETNAM_TZ)


def local_wall_time(value: datetime) -> datetime:
    return value.astimezone(VIETNAM_TZ).replace(tzinfo=None)


def iso_vietnam(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=VIETNAM_TZ)
    return value.astimezone(VIETNAM_TZ).isoformat(timespec="seconds")


def event_uuid_for(occurrence_id: int, action: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"smart-pill-box:{occurrence_id}:{action}"))


def record_device_event(
    db: Session,
    *,
    event_uuid: str,
    event_type: str,
    slot: int | None,
    virtual_time: str,
    occurrence_id: int | None = None,
    extra_payload: dict | None = None,
) -> None:
    payload = {"device_id": "SIM-001", "virtual_time": virtual_time}
    if slot is not None:
        payload["slot"] = slot
    if extra_payload:
        payload.update(extra_payload)
    db.add(
        DeviceEvent(
            event_uuid=event_uuid,
            event_type=event_type,
            occurrence_id=occurrence_id,
            payload=payload,
        )
    )


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
    occurrence_rows = db.execute(
        select(DoseOccurrence, MedicationSchedule)
        .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
        .order_by(DoseOccurrence.scheduled_at.desc(), DoseOccurrence.id.desc())
    ).all()
    active_by_slot: dict[int, tuple[DoseOccurrence, MedicationSchedule]] = {}
    latest_by_slot: dict[int, tuple[DoseOccurrence, MedicationSchedule]] = {}
    recent_occurrences = []
    for occurrence, schedule in occurrence_rows[:30]:
        latest_by_slot.setdefault(schedule.slot, (occurrence, schedule))
        if occurrence.status in ACTIVE_DOSE_STATUSES:
            active_by_slot.setdefault(schedule.slot, (occurrence, schedule))
        recent_occurrences.append(
            {
                "id": occurrence.id,
                "schedule_id": schedule.id,
                "medication_name": schedule.medication_name,
                "slot": schedule.slot,
                "scheduled_at": iso_vietnam(occurrence.scheduled_at.replace(tzinfo=VIETNAM_TZ)),
                "confirmed_at": iso_vietnam(occurrence.confirmed_at.replace(tzinfo=VIETNAM_TZ)) if occurrence.confirmed_at else None,
                "status": occurrence.status,
            }
        )

    compartments = []
    for stored in state.compartments:
        compartment = dict(stored)
        current = active_by_slot.get(compartment["slot"])
        latest = latest_by_slot.get(compartment["slot"])
        if current:
            occurrence, _ = current
            reminder = {
                "pending": "Đang nhắc",
                "reminded": "Đã nhắc lại",
                "overdue": "Quá hạn, chưa xác nhận",
            }[occurrence.status]
            compartment.update(
                led="Bật",
                buzzer_on=True,
                reminder=reminder,
                current_occurrence_id=occurrence.id,
                can_confirm=True,
            )
        else:
            last_occurrence = latest[0] if latest else None
            reminder = {
                "confirmed_on_time": "Đã xác nhận đúng hạn",
                "confirmed_late": "Đã xác nhận trễ",
            }.get(last_occurrence.status if last_occurrence else "", "Chưa đến giờ")
            compartment.update(
                led="Tắt",
                buzzer_on=False,
                reminder=reminder,
                current_occurrence_id=None,
                can_confirm=False,
            )
        compartment["compartment_id"] = compartment["slot"]
        compartments.append(compartment)

    current_dt = parse_virtual_clock(state.virtual_clock)
    wall_now = local_wall_time(current_dt)
    milestones: list[int] = []
    for occ_item in recent_occurrences:
        if occ_item["status"] in ACTIVE_DOSE_STATUSES:
            sched_dt = parse_virtual_clock(occ_item["scheduled_at"])
            sched_wall = local_wall_time(sched_dt)
            m2 = int((sched_wall + timedelta(minutes=2) - wall_now).total_seconds() // 60)
            if m2 > 0:
                milestones.append(m2)
            m5 = int((sched_wall + timedelta(minutes=5) - wall_now).total_seconds() // 60)
            if m5 > 0:
                milestones.append(m5)
    for item in active_schedules:
        hour, minute = map(int, item.time.split(":"))
        sched_time_today = wall_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        diff_min = int((sched_time_today - wall_now).total_seconds() // 60)
        if diff_min > 0:
            milestones.append(diff_min)
        else:
            diff_tomorrow = diff_min + 24 * 60
            if diff_tomorrow > 0:
                milestones.append(diff_tomorrow)
    next_milestone = min(milestones) if milestones else 1

    recent_events = db.scalars(select(DeviceEvent).order_by(DeviceEvent.id.desc()).limit(30)).all()
    return {
        "device_id": state.device_id,
        "virtual_clock": state.virtual_clock,
        "compartments": compartments,
        "next_milestone_minutes": next_milestone,
        "active_schedules": [
            {"id": item.id, "medication_name": item.medication_name, "slot": item.slot, "compartment_id": item.slot, "time": item.time}
            for item in active_schedules
        ],
        "active_occurrences": [item for item in recent_occurrences if item["status"] in ACTIVE_DOSE_STATUSES],
        "recent_occurrences": recent_occurrences,
        "recent_events": [
            {
                "id": event.id,
                "event_uuid": event.event_uuid,
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            for event in recent_events
        ],
        "idempotent": idempotent,
    }


def process_clock_minute(db: Session, point: datetime) -> None:
    wall_time = local_wall_time(point)
    schedules = db.scalars(
        select(MedicationSchedule).where(MedicationSchedule.active.is_(True))
    ).all()
    for schedule in schedules:
        if schedule.time != point.strftime("%H:%M"):
            continue
        occurrence = db.scalar(
            select(DoseOccurrence).where(
                DoseOccurrence.schedule_id == schedule.id,
                DoseOccurrence.scheduled_at == wall_time,
            )
        )
        if occurrence is None:
            occurrence = DoseOccurrence(
                schedule_id=schedule.id,
                scheduled_at=wall_time,
                status="pending",
            )
            db.add(occurrence)
            db.flush()
            record_device_event(
                db,
                event_uuid=event_uuid_for(occurrence.id, "reminder-1"),
                event_type="REMINDER_SENT",
                slot=schedule.slot,
                virtual_time=iso_vietnam(point),
                occurrence_id=occurrence.id,
                extra_payload={"schedule_id": schedule.id, "reminder_level": 1},
            )

    due_rows = db.execute(
        select(DoseOccurrence, MedicationSchedule)
        .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
        .where(
            DoseOccurrence.scheduled_at <= wall_time,
            DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
        )
    ).all()
    for occurrence, schedule in due_rows:
        elapsed = wall_time - occurrence.scheduled_at
        if elapsed >= timedelta(minutes=2) and occurrence.status == "pending":
            occurrence.status = "reminded"
            record_device_event(
                db,
                event_uuid=event_uuid_for(occurrence.id, "reminder-2"),
                event_type="REMINDER_SENT",
                slot=schedule.slot,
                virtual_time=iso_vietnam(point),
                occurrence_id=occurrence.id,
                extra_payload={"schedule_id": schedule.id, "reminder_level": 2},
            )
        if elapsed >= timedelta(minutes=5) and occurrence.status != "overdue":
            occurrence.status = "overdue"
            exists = db.scalar(
                select(Alert.id).where(
                    Alert.occurrence_id == occurrence.id,
                    Alert.kind == "dose_overdue",
                )
            )
            if exists is None:
                db.add(
                    Alert(
                        patient_id=schedule.patient_id,
                        occurrence_id=occurrence.id,
                        kind="dose_overdue",
                        message=f"Chưa xác nhận {schedule.medication_name} ở ngăn {schedule.slot}",
                    )
                )
                record_device_event(
                    db,
                    event_uuid=event_uuid_for(occurrence.id, "overdue-alert"),
                    event_type="ALERT_CREATED",
                    slot=schedule.slot,
                    virtual_time=iso_vietnam(point),
                    occurrence_id=occurrence.id,
                    extra_payload={"schedule_id": schedule.id},
                )


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
        target_slot = payload.resolved_slot
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            same_content = existing.event_type == payload.event_type and existing.payload.get("slot") == target_slot
            if not same_content:
                raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
            return state_json(db, state, idempotent=True)

        compartments = [dict(item) for item in state.compartments]
        compartment = next((item for item in compartments if item["slot"] == target_slot), None)
        if compartment is None:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy ngăn {target_slot}")
        occurrence_id = None
        extra_payload = {}

        if payload.event_type in {"LID_OPENED", "LID_CLOSED"}:
            new_open = payload.event_type == "LID_OPENED"
            if compartment["lid_open"] == new_open:
                action = "đã mở" if new_open else "đã đóng"
                raise HTTPException(status_code=409, detail=f"Nắp ngăn {target_slot} {action}")
            compartment["lid_open"] = new_open
        elif payload.event_type == "WEIGHT_READING":
            new_weight = payload.resolved_weight_g
            if new_weight is None:
                raise HTTPException(status_code=422, detail="Cần cung cấp trọng lượng weight_g")
            if not compartment["lid_open"]:
                raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {target_slot} trước khi đọc tải trọng")
            current_weight = float(compartment["weight_grams"])
            drop = round(current_weight - new_weight, 2)
            extra_payload["weight_g"] = new_weight
            if drop >= 0.3:
                if compartment["pill_count"] <= 0:
                    raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} đã hết thuốc mẫu")
                compartment["pill_count"] -= 1
                compartment["weight_grams"] = round(max(0.0, new_weight), 1)
            else:
                compartment["weight_grams"] = round(max(0.0, new_weight), 1)
        elif payload.event_type == "PILL_DISPENSED":
            if not compartment["lid_open"]:
                raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {target_slot} trước khi lấy viên")
            if compartment["pill_count"] <= 0:
                raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} đã hết thuốc mẫu")
            compartment["pill_count"] -= 1
            compartment["weight_grams"] = round(max(0.0, compartment["weight_grams"] - 0.5), 1)
        elif payload.event_type in {"DOSE_CONFIRMED", "CONFIRM_PRESSED"}:
            now = local_wall_time(parse_virtual_clock(state.virtual_clock))
            req_occ_id = payload.resolved_occurrence_id
            query = (
                select(DoseOccurrence)
                .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
                .where(
                    MedicationSchedule.slot == target_slot,
                    DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
                    DoseOccurrence.scheduled_at <= now,
                )
            )
            if req_occ_id is not None:
                query = query.where(DoseOccurrence.id == req_occ_id)
            due = db.scalar(
                query.order_by(DoseOccurrence.scheduled_at.asc(), DoseOccurrence.id.asc()).limit(1)
            )
            if due is None:
                raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} hiện không có lần nhắc cần xác nhận")
            occurrence_id = due.id
            due.confirmed_at = now
            due.status = "confirmed_late" if now - due.scheduled_at >= timedelta(minutes=5) else "confirmed_on_time"

        state.compartments = compartments
        state.updated_at = datetime.now(timezone.utc)
        record_device_event(
            db,
            event_uuid=event_uuid,
            event_type=payload.event_type,
            slot=target_slot,
            virtual_time=state.virtual_clock,
            occurrence_id=occurrence_id,
            extra_payload=extra_payload,
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)

    @app.post("/api/simulation/advance")
    @app.post("/api/simulation/clock")
    def advance_simulation_clock(
        payload: ClockAdvanceInput,
        user: User = Depends(operator_only),
        db: Session = Depends(get_db),
    ):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            same_content = existing.event_type == "CLOCK_ADVANCED" and existing.payload.get("minutes") == payload.minutes
            if not same_content:
                raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
            return state_json(db, state, idempotent=True)
        current = parse_virtual_clock(state.virtual_clock)
        for minute in range(1, payload.minutes + 1):
            process_clock_minute(db, current + timedelta(minutes=minute))
        state.virtual_clock = (current + timedelta(minutes=payload.minutes)).isoformat(timespec="seconds")
        state.updated_at = datetime.now(timezone.utc)
        record_device_event(
            db,
            event_uuid=event_uuid,
            event_type="CLOCK_ADVANCED",
            slot=None,
            virtual_time=state.virtual_clock,
            extra_payload={"minutes": payload.minutes, "previous_virtual_time": iso_vietnam(current)},
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)

    @app.post("/api/simulation/reset")
    def reset_simulation(
        payload: SimulationResetInput,
        user: User = Depends(operator_only),
        db: Session = Depends(get_db),
    ):
        if not payload.confirm:
            raise HTTPException(status_code=422, detail="Yêu cầu xác nhận confirm=true")
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            if existing.event_type != "SIMULATION_RESET":
                raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
            return state_json(db, state, idempotent=True)
        previous_clock = state.virtual_clock
        db.execute(delete(Alert))
        db.execute(delete(DeviceEvent))
        db.execute(delete(DoseOccurrence))
        state.virtual_clock = DEFAULT_SIMULATION_CLOCK
        state.compartments = default_compartments()
        state.updated_at = datetime.now(timezone.utc)
        record_device_event(
            db,
            event_uuid=event_uuid,
            event_type="SIMULATION_RESET",
            slot=None,
            virtual_time=state.virtual_clock,
            extra_payload={"previous_virtual_time": previous_clock},
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)


    return app


app = create_app()
