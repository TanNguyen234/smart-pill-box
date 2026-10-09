import re

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'from app.schemas import EventInput, LoginInput, PatientOutput, ScheduleCreate, SchedulePatch, UserOutput, ClockAdvanceInput',
    'from app.schemas import EventInput, LoginInput, PatientOutput, ScheduleCreate, SchedulePatch, UserOutput, ClockAdvanceInput, AlertOutput, AlertResolveInput'
)

new_endpoints = '''    @app.get("/api/alerts", response_model=list[AlertOutput])
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

    return app'''

content = content.replace('    return app', new_endpoints, 1)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
