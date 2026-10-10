from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, database
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Pill Box API")

@app.on_event("startup")
def on_startup():
    database.init_db()

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username, models.User.password_hash == user.password).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Sai tên đăng nhập hoặc mật khẩu")
    return {"message": "Đăng nhập thành công", "role": db_user.role, "user_id": db_user.id}

@app.post("/schedules", response_model=schemas.ScheduleResponse)
def create_schedule(schedule: schemas.ScheduleCreate, db: Session = Depends(database.get_db)):
    existing = db.query(models.Schedule).filter(
        models.Schedule.care_receiver_id == schedule.care_receiver_id,
        models.Schedule.time == schedule.time
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bị trùng giờ uống thuốc")
    
    db_schedule = models.Schedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@app.get("/schedules", response_model=List[schemas.ScheduleResponse])
def get_schedules(db: Session = Depends(database.get_db)):
    return db.query(models.Schedule).all()

@app.put("/schedules/{schedule_id}", response_model=schemas.ScheduleResponse)
def update_schedule(schedule_id: int, schedule: schemas.ScheduleCreate, db: Session = Depends(database.get_db)):
    db_schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch")
    
    for key, value in schedule.dict().items():
        setattr(db_schedule, key, value)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(database.get_db)):
    db_schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch")
    db.delete(db_schedule)
    db.commit()
    return {"message": "Đã xóa lịch thành công"}

@app.get("/events", response_model=List[schemas.EventResponse])
def get_events(db: Session = Depends(database.get_db)):
    return db.query(models.MedicationEvent).order_by(models.MedicationEvent.timestamp.desc()).all()

@app.get("/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(db: Session = Depends(database.get_db)):
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).all()

@app.patch("/alerts/{alert_id}", response_model=schemas.AlertResponse)
def update_alert_status(alert_id: int, alert_update: schemas.AlertUpdate, db: Session = Depends(database.get_db)):
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    
    valid_statuses = ["checked", "assisted", "ignored", "pending"]
    if alert_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Trạng thái không hợp lệ")
        
    db_alert.status = alert_update.status
    db.commit()
    db.refresh(db_alert)
    return db_alert
