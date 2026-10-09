import re

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('@app.post("/api/simulation/events")')
# The function ends where `return app` is, let's find that
idx_end = content.find('return app\n\n\napp = create_app()')

if idx != -1 and idx_end != -1:
    new_func = '''@app.post("/api/simulation/events")
    def simulation_event(payload: EventInput, user: User = Depends(operator_only), db: Session = Depends(get_db)):
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        if state is None:
            raise HTTPException(status_code=503, detail="Chưa khởi tạo hộp mô phỏng")
        event_uuid = str(payload.event_uuid)
        existing = db.scalar(select(DeviceEvent).where(DeviceEvent.event_uuid == event_uuid))
        if existing is not None:
            same_content = existing.event_type == payload.event_type and existing.payload.get("slot") == payload.slot
            if not same_content:
                raise HTTPException(status_code=409, detail="event_uuid đã được dùng cho sự kiện khác")
            return state_json(db, state, idempotent=True)

        compartments = [dict(item) for item in state.compartments]
        compartment = next(item for item in compartments if item["slot"] == payload.slot)
        
        try:
            current_time = datetime.fromisoformat(state.virtual_clock)
        except ValueError:
            current_time = datetime.now(timezone.utc)
            
        occurrence = None

        if payload.event_type in ["LID_OPENED", "LID_CLOSED"]:
            new_open = payload.event_type == "LID_OPENED"
            if compartment["lid_open"] == new_open:
                action = "đã mở" if new_open else "đã đóng"
                raise HTTPException(status_code=409, detail=f"Nắp ngăn {payload.slot} {action}")
            compartment["lid_open"] = new_open
            
        elif payload.event_type == "WEIGHT_CHANGED":
            if payload.weight_grams is not None:
                compartment["weight_grams"] = payload.weight_grams
                
        elif payload.event_type == "CONFIRMED":
            # Find the active occurrence for this slot
            # Actually we just look for pending occurrences for schedules of this slot
            active_schedules = db.scalars(select(MedicationSchedule).where(MedicationSchedule.slot == payload.slot, MedicationSchedule.active.is_(True))).all()
            sched_ids = [s.id for s in active_schedules]
            occurrence = db.scalar(select(DoseOccurrence).where(DoseOccurrence.schedule_id.in_(sched_ids), DoseOccurrence.status == "pending").order_by(DoseOccurrence.scheduled_at.desc()))
            
            if occurrence:
                occurrence.confirmed_at = current_time
                if current_time <= occurrence.scheduled_at + timedelta(minutes=2):
                    occurrence.status = "confirmed_on_time"
                else:
                    occurrence.status = "confirmed_late"
                
                # Turn off LED and buzzer since it's confirmed
                compartment["led"] = "Tắt"
                compartment["reminder"] = "Đã xác nhận uống"

        state.compartments = compartments
        state.updated_at = datetime.now(timezone.utc)
        
        db.add(
            DeviceEvent(
                event_uuid=event_uuid,
                event_type=payload.event_type,
                occurrence_id=occurrence.id if occurrence else None,
                payload={"device_id": "SIM-001", "slot": payload.slot, "weight_grams": payload.weight_grams},
            )
        )
        db.commit()
        db.refresh(state)
        return state_json(db, state)

    '''
    
    with open('backend/app/main.py', 'w', encoding='utf-8') as f:
        f.write(content[:idx] + new_func + content[idx_end:])
