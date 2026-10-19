import os
from datetime import date as calendar_date, datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
import math
import asyncio
import threading
from contextlib import asynccontextmanager

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import Base, make_engine, make_session_factory
from app.schema_migrations import upgrade_sqlite_schema
from app.realtime import realtime_clock_worker, tick_realtime
from app.models import Alert, DeviceEvent, DoseOccurrence, MedicationSchedule, Patient, SimulationState, User
from app.schemas import (
    AlertOutput,
    AlertPatchInput,
    AlertResolveInput,
    ClockAdvanceInput,
    ClockModeInput,
    DeviceEventOutput,
    DoseOutput,
    EventInput,
    LoginInput,
    PatientOutput,
    ScheduleCreate,
    SchedulePatch,
    SimulationResetInput,
    UserOutput,
)
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
    patient_id: int | None = None,
    extra_payload: dict | None = None,
) -> None:
    payload = {"device_id": "SIM-001", "virtual_time": virtual_time}
    if slot is not None:
        payload["slot"] = slot
    if extra_payload:
        payload.update(extra_payload)
    occurred_dt = None
    try:
        occurred_dt = parse_virtual_clock(virtual_time).replace(tzinfo=None)
    except Exception:
        pass
    db.add(
        DeviceEvent(
            event_uuid=event_uuid,
            event_type=event_type,
            device_id="SIM-001",
            slot=slot,
            occurrence_id=occurrence_id,
            patient_id=patient_id,
            payload=payload,
            occurred_at=occurred_dt,
        )
    )



def schedule_json(schedule: MedicationSchedule) -> dict:
    return {
        "id": schedule.id,
        "patient_id": schedule.patient_id,
        "medication_name": schedule.medication_name,
        "slot": schedule.slot,
        "time": schedule.time,
        "days_of_week": schedule.days_of_week,
        "active": schedule.active,
    }


def state_json(db: Session, state: SimulationState, idempotent: bool = False) -> dict:
    active_schedules = db.scalars(
        select(MedicationSchedule).where(
            MedicationSchedule.active.is_(True),
            MedicationSchedule.patient_id == state.patient_id,
        ).order_by(MedicationSchedule.time)
    ).all()
    occurrence_rows = db.execute(
        select(DoseOccurrence, MedicationSchedule)
        .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
        .where(MedicationSchedule.patient_id == state.patient_id, DoseOccurrence.clock_mode == state.clock_mode)
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
        slot_schedules = [s for s in active_schedules if s.slot == compartment["slot"]]
        if current:
            occurrence, sched = current
            compartment["medication_name"] = sched.medication_name
        elif slot_schedules:
            compartment["medication_name"] = slot_schedules[0].medication_name
        compartment["schedule_times"] = [s.time for s in slot_schedules]
        compartment["schedule_count"] = len(slot_schedules)
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
        compartment["buzzer"] = "Bật" if compartment.get("buzzer_on") else "Tắt"
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

    recent_events = db.scalars(
        select(DeviceEvent).where(DeviceEvent.patient_id == state.patient_id)
        .order_by(DeviceEvent.id.desc()).limit(30)
    ).all()
    return {
        "device_id": state.device_id,
        "virtual_clock": state.virtual_clock,
        "clock_mode": state.clock_mode,
        "compartments": compartments,
        "next_milestone_minutes": next_milestone,
        "active_schedules": [
            {
                "id": item.id,
                "medication_name": item.medication_name,
                "slot": item.slot,
                "compartment_id": item.slot,
                "time": item.time,
                "days_of_week": item.days_of_week,
            }
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


def process_clock_minute(db: Session, point: datetime, patient_id: int, clock_mode: str = "SIMULATION") -> None:
    wall_time = local_wall_time(point)
    schedules = db.scalars(
        select(MedicationSchedule).where(
            MedicationSchedule.active.is_(True), MedicationSchedule.patient_id == patient_id
        )
    ).all()
    current_weekday = point.isoweekday()
    for schedule in schedules:
        if schedule.time != point.strftime("%H:%M"):
            continue
        if schedule.days_of_week:
            allowed_days = [int(d.strip()) for d in schedule.days_of_week.split(",") if d.strip().isdigit()]
            if allowed_days and current_weekday not in allowed_days:
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
                deadline_at=wall_time + timedelta(minutes=5),
                reminder_count=1,
                status="pending",
                clock_mode=clock_mode,
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
                patient_id=schedule.patient_id,
                extra_payload={"schedule_id": schedule.id, "reminder_level": 1},
            )

    due_rows = db.execute(
        select(DoseOccurrence, MedicationSchedule)
        .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
        .where(
            DoseOccurrence.scheduled_at <= wall_time,
            DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
            DoseOccurrence.clock_mode == clock_mode,
            MedicationSchedule.patient_id == patient_id,
        )
    ).all()
    for occurrence, schedule in due_rows:
        elapsed = wall_time - occurrence.scheduled_at
        if elapsed >= timedelta(minutes=2) and occurrence.status == "pending":
            occurrence.status = "reminded"
            occurrence.reminder_count = 2
            record_device_event(
                db,
                event_uuid=event_uuid_for(occurrence.id, "reminder-2"),
                event_type="REMINDER_SENT",
                slot=schedule.slot,
                virtual_time=iso_vietnam(point),
                occurrence_id=occurrence.id,
                patient_id=schedule.patient_id,
                extra_payload={"schedule_id": schedule.id, "reminder_level": 2},
            )
        if elapsed >= timedelta(minutes=5) and occurrence.status != "overdue":
            occurrence.status = "overdue"
            occurrence.reminder_count = 2
            exists = db.scalar(
                select(Alert.id).where(
                    Alert.occurrence_id == occurrence.id,
                    Alert.kind == "dose_overdue",
                )
            )
            if exists is None:
                caregiver_id = db.scalar(select(Patient.caregiver_id).where(Patient.id == schedule.patient_id))
                db.add(
                    Alert(
                        patient_id=schedule.patient_id,
                        occurrence_id=occurrence.id,
                        recipient_id=caregiver_id,
                        kind="dose_overdue",
                        status="PENDING",
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
                    patient_id=schedule.patient_id,
                    extra_payload={"schedule_id": schedule.id},
                )



@asynccontextmanager
async def app_lifespan(app: FastAPI):
    worker = asyncio.create_task(realtime_clock_worker(app), name="smart-pill-realtime-scheduler")
    app.state.realtime_worker = worker
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass


def days_overlap(d1: str | None, d2: str | None) -> bool:
    set1 = set(d1.split(",")) if d1 else {str(i) for i in range(1, 8)}
    set2 = set(d2.split(",")) if d2 else {str(i) for i in range(1, 8)}
    return bool(set1 & set2)


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
    upgrade_sqlite_schema(engine)
    app = FastAPI(title="Smart Pill Box API", version="0.2.0", lifespan=app_lifespan)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.jwt_secret = jwt_secret
    app.state.clock_lock = threading.RLock()
    app.state.now_provider = lambda: datetime.now(VIETNAM_TZ)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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
        if payload.active:
            conflicts = db.scalars(
                select(MedicationSchedule).where(
                    MedicationSchedule.patient_id == payload.patient_id,
                    MedicationSchedule.slot == payload.slot,
                    MedicationSchedule.time == payload.time,
                    MedicationSchedule.active.is_(True),
                )
            ).all()
            for conf in conflicts:
                if days_overlap(conf.days_of_week, payload.days_of_week):
                    raise HTTPException(status_code=409, detail=f"Ngăn {payload.slot} đã có lịch uống lúc {payload.time}")
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
        target_patient_id = row.patient_id
        target_slot = changes.get("slot", row.slot)
        target_time = changes.get("time", row.time)
        target_active = changes.get("active", row.active)
        target_days = changes.get("days_of_week", row.days_of_week)
        if target_active:
            conflicts = db.scalars(
                select(MedicationSchedule).where(
                    MedicationSchedule.id != schedule_id,
                    MedicationSchedule.patient_id == target_patient_id,
                    MedicationSchedule.slot == target_slot,
                    MedicationSchedule.time == target_time,
                    MedicationSchedule.active.is_(True),
                )
            ).all()
            for conf in conflicts:
                if days_overlap(conf.days_of_week, target_days):
                    raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} đã có lịch uống lúc {target_time}")
        for key, value in changes.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return schedule_json(row)

    @app.delete("/api/schedules/{schedule_id}")
    def delete_schedule(schedule_id: int, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        row = db.get(MedicationSchedule, schedule_id)
        if row is None or db.scalar(select(Patient.id).where(Patient.id == row.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy lịch uống thuốc")
        # Remove any pending/unconfirmed occurrences for this schedule so active reminders stop
        db.execute(
            delete(DoseOccurrence).where(
                DoseOccurrence.schedule_id == schedule_id,
                DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
            )
        )
        db.delete(row)
        db.commit()
        return {"message": "Đã xóa lịch uống thuốc thành công", "deleted_id": schedule_id}

    @app.get("/api/doses", response_model=list[DoseOutput])
    def doses(
        patient_id: int | None = None,
        date: calendar_date | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id is not None:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()
        if not user_patient_ids:
            return []

        sched_ids = db.scalars(
            select(MedicationSchedule.id).where(MedicationSchedule.patient_id.in_(user_patient_ids))
        ).all()
        if not sched_ids:
            return []

        query = select(DoseOccurrence).where(DoseOccurrence.schedule_id.in_(sched_ids))
        # The Flutter "Hôm nay" screen follows the virtual clock, not the host computer date.
        demo_state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        target_date = date or (parse_virtual_clock(demo_state.virtual_clock).date() if demo_state else None)
        if target_date is not None:
            dt_start = datetime.combine(target_date, datetime.min.time())
            dt_end = dt_start + timedelta(days=1)
            query = query.where(
                DoseOccurrence.scheduled_at >= dt_start,
                DoseOccurrence.scheduled_at < dt_end,
            )
        rows = db.scalars(query.order_by(DoseOccurrence.scheduled_at.desc(), DoseOccurrence.id.desc())).all()
        return rows

    @app.get("/api/events", response_model=list[DeviceEventOutput])
    def events(
        patient_id: int | None = None,
        slot: int | None = None,
        date: calendar_date | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id is not None:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()
        if not user_patient_ids:
            return []

        # Never expose unassigned/global operator events to every caregiver.
        query = select(DeviceEvent).where(DeviceEvent.patient_id.in_(user_patient_ids))
        if slot is not None:
            query = query.where(DeviceEvent.slot == slot)
        if date is not None:
            # User-facing history is based on the simulated occurrence time.
            dt_start = datetime.combine(date, datetime.min.time())
            dt_end = dt_start + timedelta(days=1)
            query = query.where(
                DeviceEvent.occurred_at >= dt_start,
                DeviceEvent.occurred_at < dt_end,
            )
        rows = db.scalars(query.order_by(DeviceEvent.id.desc())).all()
        return rows

    @app.delete("/api/events")
    def clear_events(
        patient_id: int | None = None,
        slot: int | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id is not None:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()
        if not user_patient_ids:
            return {"status": "ok", "deleted_count": 0}

        query = select(DeviceEvent).where(DeviceEvent.patient_id.in_(user_patient_ids))
        if slot is not None:
            query = query.where(DeviceEvent.slot == slot)
        events_to_delete = db.scalars(query).all()
        count = len(events_to_delete)
        for ev in events_to_delete:
            db.delete(ev)
        db.commit()
        return {"status": "ok", "deleted_count": count}

    @app.get("/api/alerts", response_model=list[AlertOutput])
    def alerts(
        patient_id: int | None = None,
        status: str | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id is not None:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()
        if not user_patient_ids:
            return []

        query = select(Alert).where(Alert.patient_id.in_(user_patient_ids))
        if status:
            query = query.where(Alert.status == status.strip().upper())
        rows = db.scalars(query.order_by(Alert.id.desc())).all()
        return rows

    def _resolve_alert_logic(alert_id: int, note: str | None, status_val: str | None, user: User, db: Session) -> Alert:
        alert = db.get(Alert, alert_id)
        if alert is None or db.scalar(select(Patient.id).where(Patient.id == alert.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")

        target_status = (status_val or "CHECKED").strip().upper()
        if target_status == "IGNORED" and (not note or not note.strip()):
            raise HTTPException(status_code=422, detail="Cần ghi chú lý do khi bỏ qua cảnh báo")

        alert.status = target_status
        if target_status in {"CHECKED", "ASSISTED", "IGNORED"}:
            alert.resolved_at = datetime.now(timezone.utc)
        elif target_status == "PENDING":
            alert.resolved_at = None

        if note is not None:
            alert.note = note.strip() or None
        # Keep the original warning message immutable; notes are a separate field.

        db.commit()
        db.refresh(alert)
        return alert

    @app.patch("/api/alerts/{alert_id}", response_model=AlertOutput)
    def patch_alert(
        alert_id: int,
        payload: AlertPatchInput,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        return _resolve_alert_logic(alert_id, payload.note, payload.status, user, db)

    @app.post("/api/alerts/{alert_id}/resolve", response_model=AlertOutput)
    def resolve_alert(
        alert_id: int,
        payload: AlertResolveInput,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        return _resolve_alert_logic(alert_id, payload.note, "CHECKED", user, db)



    @app.post("/api/simulation/mode")
    def change_clock_mode(
        payload: ClockModeInput,
        request: Request,
        user: User = Depends(operator_only),
        db: Session = Depends(get_db),
    ):
        with request.app.state.clock_lock:
            state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
            if state is None:
                raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
            if state.clock_mode != payload.clock_mode:
                if payload.clock_mode == "REALTIME":
                    state.simulation_clock = state.virtual_clock
                    now = request.app.state.now_provider().astimezone(VIETNAM_TZ)
                    state.virtual_clock = iso_vietnam(
                        now.replace(second=0, microsecond=0) - timedelta(minutes=1)
                    )
                else:
                    state.virtual_clock = state.simulation_clock or DEFAULT_SIMULATION_CLOCK
                state.clock_mode = payload.clock_mode
                db.commit()
            if payload.clock_mode == "REALTIME":
                # Drop the reader transaction before the worker opens a writer
                # transaction on the same SQLite file.
                db.rollback()
                tick_realtime(request.app)
                db.expire_all()
                state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
            return state_json(db, state)

    @app.get("/api/simulation/state")
    @app.get("/api/simulation/clock/state")
    def simulation_state(user: User = Depends(operator_only), db: Session = Depends(get_db)):

        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        return state_json(db, state)

    @app.post("/api/simulation/events")
    def simulation_event(payload: EventInput, request: Request, user: User = Depends(operator_only), db: Session = Depends(get_db)):
        with request.app.state.clock_lock:
            state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
            if state is None:
                raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
            target_slot = payload.resolved_slot
            event_uuid = str(payload.event_uuid)
            try:
                weight_reading = payload.resolved_weight_g
                requested_occurrence = payload.resolved_occurrence_id
            except (TypeError, ValueError, OverflowError):
                raise HTTPException(status_code=422, detail="Dữ liệu cảm biến hoặc mã lần nhắc không hợp lệ")
            if weight_reading is not None and not math.isfinite(weight_reading):
                raise HTTPException(status_code=422, detail="Trọng lượng phải là số hữu hạn")
            signature = {
                "slot": target_slot,
                "event_type": payload.event_type,
                "weight_g": weight_reading,
                "occurrence_id": requested_occurrence,
                "payload": payload.payload or {},
            }
            existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
            if existing is not None:
                if existing.payload.get("request_signature") != signature:
                    raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
                return state_json(db, state, idempotent=True)

            compartments = [dict(item) for item in state.compartments]
            compartment = next((item for item in compartments if item["slot"] == target_slot), None)
            if compartment is None:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy ngăn {target_slot}")
            occurrence_id = None
            extra_payload = {"request_signature": signature}

            if payload.event_type in {"LID_OPENED", "LID_CLOSED"}:
                new_open = payload.event_type == "LID_OPENED"
                if compartment["lid_open"] == new_open:
                    action = "đã mở" if new_open else "đã đóng"
                    raise HTTPException(status_code=409, detail=f"Nắp ngăn {target_slot} {action}")
                compartment["lid_open"] = new_open

                # Khi đóng nắp ngăn, nếu thuốc đã được lấy ra trong cữ nhắc hiện tại:
                # Hệ thống tự động xác nhận liều và tắt còi báo/đèn LED ngay lập tức mà không cần nhấn nút.
                if not new_open and compartment.get("dose_taken"):
                    now = local_wall_time(parse_virtual_clock(state.virtual_clock))
                    due = db.scalar(
                        select(DoseOccurrence)
                        .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
                        .where(
                            MedicationSchedule.slot == target_slot,
                            MedicationSchedule.patient_id == state.patient_id,
                            DoseOccurrence.clock_mode == state.clock_mode,
                            DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
                            DoseOccurrence.scheduled_at <= now,
                        )
                        .order_by(DoseOccurrence.scheduled_at.asc(), DoseOccurrence.id.asc())
                        .limit(1)
                    )
                    if due is not None:
                        occurrence_id = due.id
                        due.confirmed_at = now
                        due.status = "confirmed_late" if now - due.scheduled_at >= timedelta(minutes=5) else "confirmed_on_time"
                        compartment["dose_taken"] = False
                        extra_payload["auto_confirmed"] = True
                        extra_payload["trigger"] = "LID_CLOSED"
                        auto_uuid = str(uuid5(NAMESPACE_URL, f"smart-pill-box:{due.id}:auto-confirm:{event_uuid}"))
                        record_device_event(
                            db,
                            event_uuid=auto_uuid,
                            event_type="DOSE_CONFIRMED",
                            slot=target_slot,
                            virtual_time=state.virtual_clock,
                            occurrence_id=due.id,
                            patient_id=state.patient_id,
                            extra_payload={"auto_confirmed": True, "trigger": "LID_CLOSED", "caused_by_event": event_uuid},
                        )
            elif payload.event_type in {"WEIGHT_READING", "WEIGHT_SAMPLE", "WEIGHT_CHANGED"}:
                new_weight = weight_reading
                if new_weight is None:
                    raise HTTPException(status_code=422, detail="Cần cung cấp trọng lượng weight_g")
                if new_weight < 0:
                    raise HTTPException(status_code=422, detail="Trọng lượng không được âm")
                if not compartment["lid_open"]:
                    raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {target_slot} trước khi đọc tải trọng")
                current_weight = float(compartment["weight_grams"])
                diff = round(current_weight - new_weight, 2)
                extra_payload["weight_g"] = new_weight
                if diff >= 0.3:
                    if compartment["pill_count"] <= 0:
                        raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} đã hết bịch thuốc chia sẵn")
                    compartment["pill_count"] -= 1
                    compartment["weight_grams"] = round(max(0.0, new_weight), 1)
                    compartment["dose_taken"] = True
                elif diff <= -0.4:
                    # Tăng trọng lượng đáng kể: nạp thêm bịch thuốc
                    added_pills = max(1, round(abs(diff) / 0.5))
                    compartment["pill_count"] += added_pills
                    compartment["weight_grams"] = round(max(0.0, new_weight), 1)
                    extra_payload["count"] = added_pills
                else:
                    compartment["weight_grams"] = round(max(0.0, new_weight), 1)
            elif payload.event_type in {"PILL_DISPENSED", "PILL_REMOVED"}:
                if not compartment["lid_open"]:
                    raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {target_slot} trước khi lấy bịch thuốc")
                if compartment["pill_count"] <= 0:
                    raise HTTPException(status_code=409, detail=f"Ngăn {target_slot} đã hết bịch thuốc chia sẵn")
                compartment["pill_count"] -= 1
                compartment["weight_grams"] = round(max(0.0, compartment["weight_grams"] - 0.5), 1)
                compartment["dose_taken"] = True
            elif payload.event_type in {"PILL_REFILLED", "REFILL"}:
                if not compartment["lid_open"]:
                    raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {target_slot} trước khi nạp thêm bịch thuốc")
                refill_count = payload.count or (payload.payload.get("count") if payload.payload else None) or 10
                refill_count = max(1, int(refill_count))
                added_weight = round(refill_count * 0.5, 1)
                compartment["pill_count"] += refill_count
                compartment["weight_grams"] = round(compartment["weight_grams"] + added_weight, 1)
                extra_payload["count"] = refill_count
                extra_payload["weight_added_g"] = added_weight
            elif payload.event_type in {"DOSE_CONFIRMED", "CONFIRM_PRESSED", "CONFIRMED"}:
                now = local_wall_time(parse_virtual_clock(state.virtual_clock))
                req_occ_id = requested_occurrence
                query = (
                    select(DoseOccurrence)
                    .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
                    .where(
                        MedicationSchedule.slot == target_slot,
                        MedicationSchedule.patient_id == state.patient_id,
                        DoseOccurrence.clock_mode == state.clock_mode,
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

                # Nút xác nhận trên vỏ hộp thuốc: bắt buộc người bệnh đã mở nắp và lấy thuốc ra khỏi ngăn
                if payload.event_type in {"CONFIRM_PRESSED", "CONFIRMED"} and not compartment.get("dose_taken"):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Chưa lấy bịch thuốc khỏi ngăn {target_slot}. Vui lòng mở nắp và lấy bịch thuốc trước khi xác nhận!",
                    )

                occurrence_id = due.id
                due.confirmed_at = now
                due.status = "confirmed_late" if now - due.scheduled_at >= timedelta(minutes=5) else "confirmed_on_time"
                compartment["dose_taken"] = False

            now_wall = local_wall_time(parse_virtual_clock(state.virtual_clock))
            if occurrence_id is None:
                active_occ = db.scalar(
                    select(DoseOccurrence)
                    .join(MedicationSchedule, MedicationSchedule.id == DoseOccurrence.schedule_id)
                    .where(
                        MedicationSchedule.slot == target_slot,
                        MedicationSchedule.patient_id == state.patient_id,
                        DoseOccurrence.clock_mode == state.clock_mode,
                        DoseOccurrence.status.in_(ACTIVE_DOSE_STATUSES),
                        DoseOccurrence.scheduled_at <= now_wall,
                    )
                    .order_by(DoseOccurrence.scheduled_at.desc(), DoseOccurrence.id.desc())
                    .limit(1)
                )
                if active_occ is not None:
                    occurrence_id = active_occ.id

            patient_id = state.patient_id
            if occurrence_id:
                occ_obj = db.get(DoseOccurrence, occurrence_id)
                if occ_obj:
                    sched_obj = db.get(MedicationSchedule, occ_obj.schedule_id)
                    if sched_obj:
                        patient_id = sched_obj.patient_id

            state.compartments = compartments
            state.updated_at = datetime.now(timezone.utc)
            record_device_event(
                db,
                event_uuid=event_uuid,
                event_type=payload.event_type,
                slot=target_slot,
                virtual_time=state.virtual_clock,
                occurrence_id=occurrence_id,
                patient_id=patient_id,
                extra_payload=extra_payload,
            )
            db.commit()
            db.refresh(state)
            return state_json(db, state)


    @app.post("/api/simulation/advance")
    @app.post("/api/simulation/clock")
    @app.post("/api/simulation/clock/advance")
    def advance_simulation_clock(

        payload: ClockAdvanceInput,
        request: Request,
        user: User = Depends(operator_only),
        db: Session = Depends(get_db),
    ):
        with request.app.state.clock_lock:
            state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
            if state is None:
                raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
            if state.clock_mode != "SIMULATION":
                raise HTTPException(status_code=409, detail="Đang ở chế độ thời gian thực; hãy chuyển sang Mô phỏng")
            event_uuid = str(payload.event_uuid)
            existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
            if existing is not None:
                same_content = existing.event_type == "CLOCK_ADVANCED" and existing.payload.get("minutes") == payload.minutes
                if not same_content:
                    raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
                return state_json(db, state, idempotent=True)
            current = parse_virtual_clock(state.virtual_clock)
            for minute in range(1, payload.minutes + 1):
                process_clock_minute(db, current + timedelta(minutes=minute), state.patient_id, clock_mode="SIMULATION")
            state.virtual_clock = (current + timedelta(minutes=payload.minutes)).isoformat(timespec="seconds")
            state.updated_at = datetime.now(timezone.utc)
            record_device_event(
                db,
                event_uuid=event_uuid,
                event_type="CLOCK_ADVANCED",
                slot=None,
                virtual_time=state.virtual_clock,
                patient_id=state.patient_id,
                extra_payload={"minutes": payload.minutes, "previous_virtual_time": iso_vietnam(current)},
            )
            db.commit()
            db.refresh(state)
            return state_json(db, state)

    @app.post("/api/simulation/reset")
    def reset_simulation(
        payload: SimulationResetInput,
        request: Request,
        user: User = Depends(operator_only),
        db: Session = Depends(get_db),
    ):
        with request.app.state.clock_lock:
            if not payload.confirm and payload.confirmation != "RESET_DEMO":
                raise HTTPException(status_code=422, detail="Yêu cầu xác nhận confirm=true hoặc confirmation='RESET_DEMO'")
            state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
            if state is None:
                raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
            if state.clock_mode != "SIMULATION":
                raise HTTPException(status_code=409, detail="Chuyển sang Mô phỏng trước khi reset demo")
            event_uuid = str(payload.event_uuid)
            existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
            if existing is not None:
                if existing.event_type != "SIMULATION_RESET":
                    raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho nội dung khác")
                return state_json(db, state, idempotent=True)
            previous_clock = state.virtual_clock
            # Only reset the data owned by this demo device's patient.
            demo_schedule_ids = select(MedicationSchedule.id).where(
                MedicationSchedule.patient_id == state.patient_id
            )
            demo_occurrence_ids = select(DoseOccurrence.id).where(
                DoseOccurrence.schedule_id.in_(demo_schedule_ids)
            )
            db.execute(delete(Alert).where(Alert.patient_id == state.patient_id))
            db.execute(delete(DeviceEvent).where(DeviceEvent.patient_id == state.patient_id))
            db.execute(delete(DoseOccurrence).where(DoseOccurrence.id.in_(demo_occurrence_ids)))
            state.virtual_clock = DEFAULT_SIMULATION_CLOCK
            state.simulation_clock = DEFAULT_SIMULATION_CLOCK
            state.compartments = default_compartments()
            state.updated_at = datetime.now(timezone.utc)
            record_device_event(
                db,
                event_uuid=event_uuid,
                event_type="SIMULATION_RESET",
                slot=None,
                patient_id=state.patient_id,
                virtual_time=state.virtual_clock,
                extra_payload={"previous_virtual_time": previous_clock},
            )
            db.commit()
            db.refresh(state)
            return state_json(db, state)


    return app


app = create_app()
