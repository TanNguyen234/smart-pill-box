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
from app.models import Alert, DeviceEvent, DoseOccurrence, MedicationSchedule, Patient, SimulationState, User
from app.schemas import (
    AlertOutput,
    AlertPatchInput,
    AlertResolveInput,
    ClockAdvanceInput,
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
    sched_query = select(MedicationSchedule).where(MedicationSchedule.active.is_(True))
    if state.patient_id:
        sched_query = sched_query.where(MedicationSchedule.patient_id == state.patient_id)
    active_schedules = db.scalars(sched_query.order_by(MedicationSchedule.time)).all()

    # Ensure buzzer field is included for each compartment
    compartments = []
    for comp in state.compartments:
        item = dict(comp)
        if "buzzer" not in item:
            item["buzzer"] = "Bật" if item.get("led") == "Bật" else "Tắt"
        compartments.append(item)

    return {
        "device_id": state.device_id,
        "virtual_clock": state.virtual_clock,
        "compartments": compartments,
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
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
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

    @app.get("/api/simulation/clock/state")
    def clock_state(db: Session = Depends(get_db)):
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
        slot_target = payload.slot or 1
        compartment = next((item for item in compartments if item["slot"] == slot_target), None)
        if compartment is None:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy ngăn {slot_target}")

        try:
            current_time = datetime.fromisoformat(state.virtual_clock)
        except ValueError:
            current_time = datetime.now(timezone.utc)

        occurrence = None

        if payload.event_type in ["LID_OPENED", "LID_CLOSED"]:
            new_open = payload.event_type == "LID_OPENED"
            if compartment["lid_open"] == new_open:
                action = "đã mở" if new_open else "đã đóng"
                raise HTTPException(status_code=409, detail=f"Nắp ngăn {slot_target} {action}")
            compartment["lid_open"] = new_open

        elif payload.event_type == "PILL_REMOVED":
            if not compartment["lid_open"]:
                raise HTTPException(status_code=409, detail=f"Nắp ngăn {slot_target} phải mở mới được lấy thuốc")
            if compartment.get("pill_count", 0) <= 0:
                raise HTTPException(status_code=409, detail=f"Ngăn {slot_target} đã hết thuốc")
            compartment["pill_count"] -= 1
            current_weight = float(compartment.get("weight_grams", 0.0))
            compartment["weight_grams"] = round(max(0.0, current_weight - 0.5), 1)

        elif payload.event_type in ["CONFIRM_PRESSED", "CONFIRMED"]:
            # Find active occurrence for this slot
            sched_query = select(MedicationSchedule).where(MedicationSchedule.slot == slot_target, MedicationSchedule.active.is_(True))
            if state.patient_id:
                sched_query = sched_query.where(MedicationSchedule.patient_id == state.patient_id)
            active_schedules = db.scalars(sched_query).all()
            sched_ids = [s.id for s in active_schedules]

            occurrence = db.scalar(
                select(DoseOccurrence)
                .where(
                    DoseOccurrence.schedule_id.in_(sched_ids),
                    DoseOccurrence.status.in_(["REMINDING", "pending", "SCHEDULED", "UNCONFIRMED"]),
                )
                .order_by(DoseOccurrence.scheduled_at.desc())
            )

            if occurrence:
                occurrence.confirmed_at = current_time
                deadline = occurrence.deadline_at or (occurrence.scheduled_at + timedelta(minutes=5))
                if deadline.tzinfo is None and current_time.tzinfo is not None:
                    deadline = deadline.replace(tzinfo=current_time.tzinfo)
                elif deadline.tzinfo is not None and current_time.tzinfo is None:
                    current_time_cmp = current_time.replace(tzinfo=deadline.tzinfo)
                else:
                    current_time_cmp = current_time

                if current_time_cmp <= deadline:
                    occurrence.status = "CONFIRMED"
                else:
                    occurrence.status = "CONFIRMED_LATE"

            compartment["led"] = "Tắt"
            compartment["buzzer"] = "Tắt"
            compartment["reminder"] = "Đã xác nhận uống"

        elif payload.event_type in ["WEIGHT_CHANGED", "WEIGHT_SAMPLE"]:
            if payload.weight_grams is not None:
                compartment["weight_grams"] = payload.weight_grams

        state.compartments = compartments
        state.updated_at = datetime.now(timezone.utc)

        db.add(
            DeviceEvent(
                event_uuid=event_uuid,
                event_type=payload.event_type,
                patient_id=state.patient_id,
                slot=slot_target,
                occurrence_id=occurrence.id if occurrence else None,
                occurred_at=current_time,
                payload={
                    "device_id": "SIM-001",
                    "slot": slot_target,
                    "weight_grams": payload.weight_grams or compartment.get("weight_grams"),
                    "pill_count": compartment.get("pill_count"),
                },
            )
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)

    def _advance_logic(payload: ClockAdvanceInput, db: Session):
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
        sched_query = select(MedicationSchedule).where(MedicationSchedule.active.is_(True))
        if state.patient_id:
            sched_query = sched_query.where(MedicationSchedule.patient_id == state.patient_id)
        active_schedules = db.scalars(sched_query).all()

        compartments = [dict(c) for c in state.compartments]

        # 1. Check for scheduled occurrences crossed
        for sched in active_schedules:
            hour, minute = map(int, sched.time.split(":"))
            sched_datetime = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if current_time < sched_datetime <= new_time:
                # Check if occurrence already exists to prevent duplication
                existing_occ = db.scalar(
                    select(DoseOccurrence).where(
                        DoseOccurrence.schedule_id == sched.id,
                        DoseOccurrence.scheduled_at == sched_datetime,
                    )
                )
                if existing_occ is None:
                    occurrence = DoseOccurrence(
                        schedule_id=sched.id,
                        scheduled_at=sched_datetime,
                        deadline_at=sched_datetime + timedelta(minutes=5),
                        status="REMINDING",
                        reminder_count=1,
                    )
                    db.add(occurrence)

                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["led"] = "Bật"
                        comp["buzzer"] = "Bật"
                        comp["reminder"] = f"Đến giờ {sched.time}"

                passed_milestones.append({
                    "ngan": sched.slot,
                    "thuoc": sched.medication_name,
                    "thoi_gian_nhac": sched.time,
                    "trang_thai": "Tới giờ uống thuốc, còi và đèn đã bật (Mô phỏng)",
                })

        db.flush()

        # 2. Check for overdue unconfirmed occurrences
        pending_occurrences = db.scalars(
            select(DoseOccurrence).where(DoseOccurrence.status.in_(["REMINDING", "pending", "SCHEDULED"]))
        ).all()

        for occ in pending_occurrences:
            scheduled_at = occ.scheduled_at
            new_time_cmp = new_time
            if scheduled_at.tzinfo is None and new_time.tzinfo is not None:
                scheduled_at = scheduled_at.replace(tzinfo=new_time.tzinfo)
            elif scheduled_at.tzinfo is not None and new_time.tzinfo is None:
                new_time_cmp = new_time.replace(tzinfo=scheduled_at.tzinfo)
            delay = (new_time_cmp - scheduled_at).total_seconds() / 60.0
            sched = db.get(MedicationSchedule, occ.schedule_id)
            if not sched:
                continue

            # Sau 2 phút chưa xác nhận -> Nhắc lại lần 2
            if 2 <= delay < 5:
                was_count = occ.reminder_count
                occ.reminder_count = 2
                for comp in compartments:
                    if comp["slot"] == sched.slot and comp.get("reminder") != "Đã xác nhận uống":
                        comp["reminder"] = f"NHẮC LẠI: Đã trễ {int(delay)} phút!"
                        comp["led"] = "Bật"
                        comp["buzzer"] = "Bật"

                if was_count < 2:
                    passed_milestones.append({
                        "ngan": sched.slot,
                        "thuoc": sched.medication_name,
                        "thoi_gian_nhac": f"{sched.time} (+{int(delay)} phút)",
                        "trang_thai": f"Nhắc lại lần 2: Đã trễ {int(delay)} phút chưa xác nhận uống!",
                    })

            # Sau 5 phút chưa xác nhận -> Quá hạn, tắt đèn/còi, tạo Alert
            if delay >= 5:
                occ.status = "UNCONFIRMED"
                patient = db.get(Patient, sched.patient_id)
                recipient_id = patient.caregiver_id if patient else None

                existing_alert = db.scalar(select(Alert).where(Alert.occurrence_id == occ.id))
                if not existing_alert:
                    new_alert = Alert(
                        patient_id=sched.patient_id,
                        occurrence_id=occ.id,
                        recipient_id=recipient_id,
                        kind="MISSED_CONFIRMATION",
                        status="PENDING",
                        message=f"Quá hạn 5 phút chưa xác nhận uống {sched.medication_name} (Ngăn {sched.slot})",
                    )
                    db.add(new_alert)
                    passed_milestones.append({
                        "ngan": sched.slot,
                        "thuoc": sched.medication_name,
                        "thoi_gian_nhac": sched.time,
                        "trang_thai": "Đã tạo cảnh báo quá hạn gửi đến người thân!",
                    })

                for comp in compartments:
                    if comp["slot"] == sched.slot:
                        comp["led"] = "Tắt"
                        comp["buzzer"] = "Tắt"
                        comp["reminder"] = "Đã quá hạn (Chưa uống)"

        state.compartments = compartments
        db.commit()
        db.refresh(state)

        result = state_json(db, state)
        result["passed_milestones"] = passed_milestones
        return result

    @app.post("/api/simulation/advance")
    def advance_time(payload: ClockAdvanceInput, db: Session = Depends(get_db)):
        return _advance_logic(payload, db)

    @app.post("/api/simulation/clock/advance")
    def advance_clock_alias(payload: ClockAdvanceInput, db: Session = Depends(get_db)):
        return _advance_logic(payload, db)

    @app.post("/api/simulation/reset")
    def simulation_reset(
        payload: SimulationResetInput,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(get_db),
    ):
        if payload.confirmation != "RESET_DEMO":
            raise HTTPException(status_code=400, detail="Cần xác nhận 'RESET_DEMO'")

        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")

        # Reset virtual clock
        state.virtual_clock = "2026-10-09T07:59:00+07:00"
        state.updated_at = datetime.now(timezone.utc)
        state.compartments = [
            {"slot": 1, "medication_name": "Thuốc A", "pill_count": 10, "weight_grams": 5.0, "lid_open": False, "led": "Tắt", "buzzer": "Tắt", "reminder": "Chưa đến giờ"},
            {"slot": 2, "medication_name": "Thuốc B", "pill_count": 8, "weight_grams": 4.0, "lid_open": False, "led": "Tắt", "buzzer": "Tắt", "reminder": "Chưa đến giờ"},
            {"slot": 3, "medication_name": "Thuốc C", "pill_count": 12, "weight_grams": 6.0, "lid_open": False, "led": "Tắt", "buzzer": "Tắt", "reminder": "Chưa đến giờ"},
        ]

        # Clean demo dose occurrences, events, alerts for patient A
        if state.patient_id:
            schedules_p = db.scalars(select(MedicationSchedule.id).where(MedicationSchedule.patient_id == state.patient_id)).all()
            if schedules_p:
                occ_ids = db.scalars(select(DoseOccurrence.id).where(DoseOccurrence.schedule_id.in_(schedules_p))).all()
                if occ_ids:
                    alerts = db.scalars(select(Alert).where(Alert.occurrence_id.in_(occ_ids))).all()
                    for a in alerts:
                        db.delete(a)
                    events = db.scalars(select(DeviceEvent).where(DeviceEvent.occurrence_id.in_(occ_ids))).all()
                    for e in events:
                        db.delete(e)
                    occs = db.scalars(select(DoseOccurrence).where(DoseOccurrence.id.in_(occ_ids))).all()
                    for o in occs:
                        db.delete(o)

            # Also delete orphaned device events for this patient
            p_events = db.scalars(select(DeviceEvent).where(DeviceEvent.patient_id == state.patient_id)).all()
            for e in p_events:
                db.delete(e)

        db.commit()
        db.refresh(state)
        return state_json(db, state)

    @app.get("/api/doses", response_model=list[DoseOutput])
    def get_doses(
        patient_id: int | None = None,
        date: str | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()

        if not user_patient_ids:
            return []

        sched_ids = db.scalars(select(MedicationSchedule.id).where(MedicationSchedule.patient_id.in_(user_patient_ids))).all()
        query = select(DoseOccurrence).where(DoseOccurrence.schedule_id.in_(sched_ids))
        rows = db.scalars(query.order_by(DoseOccurrence.scheduled_at.desc())).all()
        return rows

    @app.get("/api/events", response_model=list[DeviceEventOutput])
    def get_events(
        patient_id: int | None = None,
        slot: int | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()

        if not user_patient_ids:
            return []

        query = select(DeviceEvent).where(DeviceEvent.patient_id.in_(user_patient_ids))
        if slot:
            query = query.where(DeviceEvent.slot == slot)
        rows = db.scalars(query.order_by(DeviceEvent.created_at.desc())).all()
        return rows

    @app.get("/api/alerts", response_model=list[AlertOutput])
    def get_alerts(
        patient_id: int | None = None,
        status: str | None = None,
        user: User = Depends(caregiver_only),
        db: Session = Depends(get_db),
    ):
        p_query = select(Patient.id).where(Patient.caregiver_id == user.id)
        if patient_id:
            p_query = p_query.where(Patient.id == patient_id)
        user_patient_ids = db.scalars(p_query).all()

        if not user_patient_ids:
            return []

        query = select(Alert).where(Alert.patient_id.in_(user_patient_ids))
        if status:
            query = query.where(Alert.status == status)
        rows = db.scalars(query.order_by(Alert.created_at.desc())).all()
        return rows

    def _resolve_alert_logic(alert_id: int, note: str | None, status_val: str | None, user: User, db: Session):
        alert = db.get(Alert, alert_id)
        if not alert or db.scalar(select(Patient.id).where(Patient.id == alert.patient_id, Patient.caregiver_id == user.id)) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")

        if status_val == "IGNORED" and (not note or not note.strip()):
            raise HTTPException(status_code=422, detail="Cần ghi chú lý do khi bỏ qua cảnh báo")

        alert.resolved_at = datetime.now(timezone.utc)
        alert.status = status_val or "CHECKED"
        if note:
            alert.note = note
            alert.message += f" (Ghi chú: {note})"

        db.commit()
        db.refresh(alert)
        return alert

    @app.patch("/api/alerts/{alert_id}", response_model=AlertOutput)
    def patch_alert(alert_id: int, payload: AlertPatchInput, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        return _resolve_alert_logic(alert_id, payload.note, payload.status, user, db)

    @app.post("/api/alerts/{alert_id}/resolve", response_model=AlertOutput)
    def resolve_alert(alert_id: int, payload: AlertResolveInput, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
        return _resolve_alert_logic(alert_id, payload.note, "CHECKED", user, db)

    return app


app = create_app()
