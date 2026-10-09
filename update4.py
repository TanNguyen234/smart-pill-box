import re

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure Alert is imported
if 'Alert' not in content:
    content = content.replace('User, DoseOccurrence', 'User, DoseOccurrence, Alert')

new_logic = '''        passed_milestones = []
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

        state.compartments = compartments'''

content = re.sub(r'        passed_milestones = \[\]\n        active_schedules = db\.scalars.*?\)\n', new_logic + '\n', content, flags=re.DOTALL)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
