from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import caregiver_only, get_db
from app.models import MedicationSchedule, Patient, User
from app.schemas import PatientOutput, ScheduleCreate, SchedulePatch

router = APIRouter(tags=["2. Hồ sơ & Lịch uống thuốc (Vai trò 1)"])


def schedule_json(schedule: MedicationSchedule) -> dict:
    return {
        "id": schedule.id,
        "patient_id": schedule.patient_id,
        "medication_name": schedule.medication_name,
        "slot": schedule.slot,
        "time": schedule.time,
        "active": schedule.active,
    }


@router.get(
    "/api/patients",
    response_model=list[PatientOutput],
    summary="Lấy danh sách hồ sơ bệnh nhân thuộc Caregiver",
)
def patients(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    return db.scalars(
        select(Patient).where(Patient.caregiver_id == user.id).order_by(Patient.id)
    ).all()


@router.get(
    "/api/schedules",
    summary="Lấy danh sách lịch uống thuốc theo quyền Caregiver",
)
def schedules(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    patient_ids = select(Patient.id).where(Patient.caregiver_id == user.id)
    rows = db.scalars(
        select(MedicationSchedule)
        .where(MedicationSchedule.patient_id.in_(patient_ids))
        .order_by(MedicationSchedule.time)
    ).all()
    return [schedule_json(row) for row in rows]


@router.post(
    "/api/schedules",
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lịch uống thuốc mới (kiểm tra quyền & chống trùng giờ/ngăn đang bật)",
)
def create_schedule(
    payload: ScheduleCreate,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    patient = db.get(Patient, payload.patient_id)
    if patient is None or patient.caregiver_id != user.id:
        raise HTTPException(status_code=403, detail="Hồ sơ không thuộc tài khoản này")
    if payload.active:
        duplicate = db.scalar(
            select(MedicationSchedule.id).where(
                MedicationSchedule.patient_id == payload.patient_id,
                MedicationSchedule.slot == payload.slot,
                MedicationSchedule.time == payload.time,
                MedicationSchedule.active.is_(True),
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Đã có lịch uống thuốc đang bật trùng ngăn và giờ cho hồ sơ này",
            )
    row = MedicationSchedule(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return schedule_json(row)


@router.patch(
    "/api/schedules/{schedule_id}",
    summary="Cập nhật lịch uống thuốc (kiểm tra quyền & chống trùng giờ/ngăn đang bật)",
)
def update_schedule(
    schedule_id: int,
    payload: SchedulePatch,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    row = db.get(MedicationSchedule, schedule_id)
    if (
        row is None
        or db.scalar(
            select(Patient.id).where(
                Patient.id == row.patient_id, Patient.caregiver_id == user.id
            )
        )
        is None
    ):
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch")
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(
            status_code=422, detail="Cần ít nhất một giá trị cập nhật hợp lệ"
        )
    target_slot = changes.get("slot", row.slot)
    target_time = changes.get("time", row.time)
    target_active = changes.get("active", row.active)
    if target_active:
        duplicate = db.scalar(
            select(MedicationSchedule.id).where(
                MedicationSchedule.id != row.id,
                MedicationSchedule.patient_id == row.patient_id,
                MedicationSchedule.slot == target_slot,
                MedicationSchedule.time == target_time,
                MedicationSchedule.active.is_(True),
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Đã có lịch uống thuốc đang bật trùng ngăn và giờ cho hồ sơ này",
            )
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return schedule_json(row)
