from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_only
from app.models import Alert, DeviceEvent, DoseOccurrence, MedicationSchedule, SimulationState, User
from app.schemas import ClockAdvanceInput, EventInput, SimulationResetInput
from app.seed import DEFAULT_SIMULATION_CLOCK, default_compartments

router = APIRouter(tags=["3. Mô phỏng Hộp thuốc & Đồng hồ ảo (Vai trò 2 & 3)"])

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


@router.get("/api/simulation/state", summary="Lấy trạng thái hộp thuốc mô phỏng")
def simulation_state(user: User = Depends(operator_only), db: Session = Depends(get_db)):
    state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
    if state is None:
        raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
    return state_json(db, state)


@router.post("/api/simulation/events", summary="Gửi sự kiện phần cứng mô phỏng (mở/đóng nắp, cân, xác nhận)")
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
    elif payload.event_type in {"WEIGHT_READING", "WEIGHT_SAMPLE"}:
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
    elif payload.event_type in {"PILL_DISPENSED", "PILL_REMOVED"}:
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


@router.post("/api/simulation/advance", summary="Tiến đồng hồ mô phỏng theo phút")
@router.post("/api/simulation/clock", summary="Tiến đồng hồ mô phỏng theo phút (alias)")
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


@router.post("/api/simulation/reset", summary="Đặt lại đồng hồ và 3 ngăn thuốc về trạng thái ban đầu")
def reset_simulation(
    payload: SimulationResetInput,
    user: User = Depends(operator_only),
    db: Session = Depends(get_db),
):
    if not payload.confirm and payload.confirmation != "RESET_DEMO":
        raise HTTPException(status_code=422, detail="Yêu cầu xác nhận confirm=true hoặc confirmation='RESET_DEMO'")
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
