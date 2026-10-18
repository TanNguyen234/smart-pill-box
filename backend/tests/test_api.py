from sqlalchemy import func, inspect, select
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Alert, DeviceEvent, DoseOccurrence, MedicationSchedule
from app.seed import seed_demo


def make_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.sqlite3'}"
    app = create_app(database_url=database_url, jwt_secret="test-secret-for-tests")
    seed_demo(app.state.session_factory, "demo-test-password")
    return TestClient(app)


def login(client, email):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "demo-test-password"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_login_and_role_scoped_schedules(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/health").status_code == 200
    assert client.post(
        "/api/auth/login", json={"email": "caregiver-a@example.test", "password": "wrong"}
    ).status_code == 401

    caregiver_a = login(client, "caregiver-a@example.test")
    caregiver_b = login(client, "caregiver-b@example.test")
    patient_a = client.get("/api/patients", headers=caregiver_a).json()[0]
    patient_b = client.get("/api/patients", headers=caregiver_b).json()[0]
    assert {row["patient_id"] for row in client.get("/api/schedules", headers=caregiver_a).json()} == {
        patient_a["id"]
    }

    created = client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": patient_a["id"], "medication_name": "Thuốc D", "slot": 1, "time": "08:10", "active": True},
    )
    assert created.status_code == 201
    assert created.json()["medication_name"] == "Thuốc D"
    assert any(
        row["medication_name"] == "Thuốc D" and row["time"] == "08:10"
        for row in client.get("/api/schedules", headers=caregiver_a).json()
    )
    assert client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": patient_b["id"], "medication_name": "Không được phép", "slot": 1, "time": "08:10"},
    ).status_code == 403
    assert client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": patient_a["id"], "medication_name": "Sai ngăn", "slot": 4, "time": "08:10"},
    ).status_code == 422
    assert client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": patient_a["id"], "medication_name": "Sai giờ", "slot": 1, "time": "24:00"},
    ).status_code == 422

    schedule_b = client.get("/api/schedules", headers=caregiver_b).json()[0]
    assert client.patch(
        f"/api/schedules/{schedule_b['id']}", headers=caregiver_a, json={"time": "09:00"}
    ).status_code == 404

    assert client.get("/api/simulation/state", headers=caregiver_a).status_code == 403
    assert client.post(
        "/api/simulation/events",
        headers=caregiver_a,
        json={"event_uuid": "ace616e6-cc5b-4904-9f84-115f22e3b15a", "slot": 1, "event_type": "LID_OPENED"},
    ).status_code == 403
    assert client.get("/api/me", headers=caregiver_a).json()["role"] == "caregiver"


def test_operator_events_are_idempotent_persistent_and_validated(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver_a = login(client, "caregiver-a@example.test")
    patient_a = client.get("/api/patients", headers=caregiver_a).json()[0]
    schedule = client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": patient_a["id"], "medication_name": "Thuốc D", "slot": 1, "time": "08:10"},
    )
    assert schedule.status_code == 201
    state = client.get("/api/simulation/state", headers=operator)
    assert state.status_code == 200
    assert state.json()["device_id"] == "SIM-001"
    assert len(state.json()["compartments"]) == 3

    event = {"event_uuid": "7b5767d1-6fa5-46ee-8fda-44a693cb8171", "slot": 1, "event_type": "LID_OPENED"}
    opened = client.post("/api/simulation/events", headers=operator, json=event)
    assert opened.status_code == 200
    assert opened.json()["compartments"][0]["lid_open"] is True
    assert client.post("/api/simulation/events", headers=operator, json=event).json()["idempotent"] is True
    assert client.post(
        "/api/simulation/events", headers=operator, json={**event, "event_type": "LID_CLOSED"}
    ).status_code == 409
    assert client.post("/api/simulation/events", headers=operator, json={**event, "slot": 4}).status_code == 422
    assert client.post(
        "/api/simulation/events",
        headers=operator,
        json={**event, "event_uuid": "9cce2ee6-4048-43e7-a4ee-49818938fbe1"},
    ).status_code == 409
    closed = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "8c063e12-6001-4f61-8bbc-bde960eec32e", "slot": 1, "event_type": "LID_CLOSED"},
    )
    assert closed.status_code == 200
    assert closed.json()["compartments"][0]["lid_open"] is False

    restarted = create_app(
        database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}", jwt_secret="test-secret-for-tests"
    )
    restarted_client = TestClient(restarted)
    persisted = restarted_client.get("/api/simulation/state", headers=operator).json()
    assert persisted["compartments"][0]["lid_open"] is False
    with restarted.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DeviceEvent)) == 2
    assert set(inspect(restarted.state.engine).get_table_names()) == {
        "users", "patients", "medication_schedules", "dose_occurrences",
        "device_events", "alerts", "simulation_state",
    }
    assert any(row["medication_name"] == "Thuốc D" for row in restarted_client.get("/api/schedules", headers=caregiver_a).json())


def test_operator_simulation_controls_are_persistent_and_idempotent(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")

    initial = client.get("/api/simulation/state", headers=operator).json()
    assert initial["virtual_clock"] == "2026-10-09T07:59:00+07:00"
    assert len(initial["compartments"]) == 3
    assert initial["recent_events"] == []

    closed_dispense = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "f6f69e78-563a-4aee-8cc9-9afe4976e762", "slot": 1, "event_type": "PILL_DISPENSED"},
    )
    assert closed_dispense.status_code == 409

    opened = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "9f984b60-d939-4f2e-9dc4-5168c708969f", "slot": 1, "event_type": "LID_OPENED"},
    )
    assert opened.status_code == 200
    dispensed_event = {
        "event_uuid": "e0a4a139-c8be-45cb-b345-654f3f474207",
        "slot": 1,
        "event_type": "PILL_DISPENSED",
    }
    dispensed = client.post("/api/simulation/events", headers=operator, json=dispensed_event)
    assert dispensed.status_code == 200
    assert dispensed.json()["compartments"][0]["pill_count"] == 9
    assert dispensed.json()["compartments"][0]["weight_grams"] == 4.5
    replay = client.post("/api/simulation/events", headers=operator, json=dispensed_event)
    assert replay.status_code == 200
    assert replay.json()["idempotent"] is True
    assert replay.json()["compartments"][0]["pill_count"] == 9

    at_dose_time = client.post(
        "/api/simulation/clock",
        headers=operator,
        json={"event_uuid": "8fb5112e-a51d-43f7-a9de-fc2f71bd39ac", "minutes": 1},
    )
    assert at_dose_time.status_code == 200
    state = at_dose_time.json()
    assert state["virtual_clock"] == "2026-10-09T08:00:00+07:00"
    assert state["compartments"][0]["led"] == "Bật"
    assert state["compartments"][0]["buzzer_on"] is True
    assert len(state["active_occurrences"]) == 1
    clock_retry = client.post(
        "/api/simulation/clock",
        headers=operator,
        json={"event_uuid": "8fb5112e-a51d-43f7-a9de-fc2f71bd39ac", "minutes": 1},
    )
    assert clock_retry.status_code == 200
    assert clock_retry.json()["virtual_clock"] == "2026-10-09T08:00:00+07:00"
    assert clock_retry.json()["idempotent"] is True
    assert client.post(
        "/api/simulation/clock",
        headers=operator,
        json={"event_uuid": "8fb5112e-a51d-43f7-a9de-fc2f71bd39ac", "minutes": 2},
    ).status_code == 409

    reminded = client.post(
        "/api/simulation/clock",
        headers=operator,
        json={"event_uuid": "9392e95a-3afe-48e1-bf31-24d800d14609", "minutes": 2},
    )
    assert reminded.status_code == 200
    assert reminded.json()["compartments"][0]["reminder"] == "Đã nhắc lại"

    overdue = client.post(
        "/api/simulation/clock",
        headers=operator,
        json={"event_uuid": "9a9e1440-34cb-4ddd-89a8-b27ac836be5d", "minutes": 3},
    )
    assert overdue.status_code == 200
    assert overdue.json()["compartments"][0]["reminder"] == "Quá hạn, chưa xác nhận"
    with client.app.state.session_factory() as db:
        assert db.query(Alert).count() == 1
        occurrence = db.query(DoseOccurrence).one()
        assert occurrence.status == "overdue"

    confirmed = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "7fb28731-00e1-4c5f-8a1c-c2c5b9436f81", "slot": 1, "event_type": "DOSE_CONFIRMED"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["compartments"][0]["led"] == "Tắt"
    assert confirmed.json()["compartments"][0]["buzzer_on"] is False
    with client.app.state.session_factory() as db:
        assert db.query(Alert).count() == 1
        assert db.query(DoseOccurrence).one().status == "confirmed_late"
        assert db.query(DeviceEvent).count() == 9

    reset_event_uuid = "6c9b3d08-99f4-4019-b18e-071394031194"
    reset = client.post(
        "/api/simulation/reset", headers=operator, json={"event_uuid": reset_event_uuid, "confirm": True}
    )
    assert reset.status_code == 200
    reset_state = reset.json()
    assert reset_state["virtual_clock"] == "2026-10-09T07:59:00+07:00"
    assert reset_state["compartments"][0]["pill_count"] == 10
    assert reset_state["compartments"][0]["weight_grams"] == 5.0
    assert [event["event_type"] for event in reset_state["recent_events"]] == ["SIMULATION_RESET"]
    with client.app.state.session_factory() as db:
        assert db.query(Alert).count() == 0
        assert db.query(DoseOccurrence).count() == 0
        assert db.query(DeviceEvent).count() == 1
        assert db.query(MedicationSchedule).count() == 4
    reset_retry = client.post(
        "/api/simulation/reset", headers=operator, json={"event_uuid": reset_event_uuid, "confirm": True}
    )
    assert reset_retry.json()["idempotent"] is True


def test_simulation_clock_and_confirmation_validate_permissions_and_state(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver = login(client, "caregiver-a@example.test")

    assert client.post("/api/simulation/clock", headers=operator, json={"event_uuid": "205fe391-cb71-4212-ab7e-302d3afc84c2", "minutes": 0}).status_code == 422
    assert client.post("/api/simulation/clock", headers=operator, json={"event_uuid": "1d64c71a-4396-4322-9147-6a45ec9b3410", "minutes": 61}).status_code == 422
    assert client.post("/api/simulation/clock", headers=caregiver, json={"event_uuid": "8201b37b-4c8d-467b-94dc-e632a01e370a", "minutes": 1}).status_code == 403
    assert client.post("/api/simulation/reset", headers=caregiver, json={"event_uuid": "414da1a7-855c-40fd-a1fe-b900df3a53b9"}).status_code == 403
    assert client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "b021be1c-17a6-461c-9f35-a1f346d96f7c", "slot": 1, "event_type": "DOSE_CONFIRMED"},
    ).status_code == 409

    due = client.post("/api/simulation/clock", headers=operator, json={"event_uuid": "1c8dfe0c-5215-43aa-a5c9-e1fc840f443c", "minutes": 1})
    assert due.status_code == 200
    confirmed = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"event_uuid": "b021be1c-17a6-461c-9f35-a1f346d96f7d", "slot": 1, "event_type": "DOSE_CONFIRMED"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["compartments"][0]["reminder"] == "Đã xác nhận đúng hạn"
    with client.app.state.session_factory() as db:
        assert db.query(DoseOccurrence).one().status == "confirmed_on_time"

    persisted = client.get("/api/simulation/state", headers=operator).json()
    assert persisted["compartments"][0]["reminder"] == "Đã xác nhận đúng hạn"
    assert [event["event_type"] for event in persisted["recent_events"]].count("REMINDER_SENT") == 1


def test_hardware_events_and_noise_threshold(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")

    opened = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"compartment_id": 1, "event_type": "LID_OPENED"},
    )
    assert opened.status_code == 200

    # Test noise reading: 5.0g -> 4.9g (drop of 0.1g < 0.3g threshold)
    noise = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"compartment_id": 1, "event_type": "WEIGHT_READING", "payload": {"weight_g": 4.9}},
    )
    assert noise.status_code == 200
    comp1 = noise.json()["compartments"][0]
    assert comp1["weight_grams"] == 4.9
    assert comp1["pill_count"] == 10  # Pill count must NOT decrease

    # Test pill retrieval: 4.9g -> 4.4g (drop of 0.5g >= 0.3g threshold)
    retrieval = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"compartment_id": 1, "event_type": "WEIGHT_READING", "payload": {"weight_g": 4.4}},
    )
    assert retrieval.status_code == 200
    comp1 = retrieval.json()["compartments"][0]
    assert comp1["weight_grams"] == 4.4
    assert comp1["pill_count"] == 9  # Pill count decreased by 1

    # Test advance endpoint /api/simulation/advance
    adv = client.post(
        "/api/simulation/advance",
        headers=operator,
        json={"minutes": 1},
    )
    assert adv.status_code == 200
    assert adv.json()["virtual_clock"] == "2026-10-09T08:00:00+07:00"

    # Test CONFIRM_PRESSED
    confirmed = client.post(
        "/api/simulation/events",
        headers=operator,
        json={"compartment_id": 1, "event_type": "CONFIRM_PRESSED"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["compartments"][0]["reminder"] == "Đã xác nhận đúng hạn"


def test_schedule_collision_and_scoping(tmp_path):
    client = make_client(tmp_path)
    caregiver_a = login(client, "caregiver-a@example.test")
    caregiver_b = login(client, "caregiver-b@example.test")

    # Patient 1 already has slot 1 at 08:00 active (from seed)
    dup = client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": 1, "medication_name": "Thuốc Trùng", "slot": 1, "time": "08:00", "active": True},
    )
    assert dup.status_code == 409
    assert "đã có lịch uống" in dup.json()["detail"]

    # Valid new schedule at 08:30
    created = client.post(
        "/api/schedules",
        headers=caregiver_a,
        json={"patient_id": 1, "medication_name": "Thuốc Mới", "slot": 1, "time": "08:30", "active": True},
    )
    assert created.status_code == 201
    new_id = created.json()["id"]

    # Try patching new schedule to collide with 08:00
    patch_dup = client.patch(
        f"/api/schedules/{new_id}",
        headers=caregiver_a,
        json={"time": "08:00"},
    )
    assert patch_dup.status_code == 409

    # Caregiver B cannot touch Patient 1
    unauthorized_create = client.post(
        "/api/schedules",
        headers=caregiver_b,
        json={"patient_id": 1, "medication_name": "Thuốc Hack", "slot": 3, "time": "15:00", "active": True},
    )
    assert unauthorized_create.status_code == 403

    unauthorized_patch = client.patch(
        f"/api/schedules/{new_id}",
        headers=caregiver_b,
        json={"time": "16:00"},
    )
    assert unauthorized_patch.status_code == 404


def test_doses_events_alerts_endpoints_and_permissions(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver_a = login(client, "caregiver-a@example.test")
    caregiver_b = login(client, "caregiver-b@example.test")

    # Advance clock to 08:00 to trigger DoseOccurrence for slot 1
    adv = client.post("/api/simulation/clock/advance", headers=operator, json={"minutes": 1})
    assert adv.status_code == 200

    # Caregiver A queries /api/doses
    doses_res = client.get("/api/doses", headers=caregiver_a)
    assert doses_res.status_code == 200
    doses = doses_res.json()
    assert len(doses) >= 1
    assert doses[0]["status"] == "pending"

    # Caregiver B queries /api/doses -> Patient 2 has no dose at 08:00
    b_doses = client.get("/api/doses", headers=caregiver_b).json()
    assert len(b_doses) == 0

    # Advance clock 5 minutes -> status overdue and Alert created
    client.post("/api/simulation/advance", headers=operator, json={"minutes": 5})

    # Caregiver A gets /api/alerts
    alerts_res = client.get("/api/alerts", headers=caregiver_a)
    assert alerts_res.status_code == 200
    alerts_list = alerts_res.json()
    assert len(alerts_list) == 1
    alert_id = alerts_list[0]["id"]
    assert alerts_list[0]["status"] == "PENDING"
    assert alerts_list[0]["resolved_at"] is None

    # Caregiver B cannot see this alert
    b_alerts = client.get("/api/alerts", headers=caregiver_b).json()
    assert len(b_alerts) == 0

    # Caregiver B cannot patch this alert
    b_patch = client.patch(f"/api/alerts/{alert_id}", headers=caregiver_b, json={"status": "CHECKED"})
    assert b_patch.status_code == 404

    # Patch with IGNORED but without note -> 422
    err_patch = client.patch(f"/api/alerts/{alert_id}", headers=caregiver_a, json={"status": "IGNORED", "note": "   "})
    assert err_patch.status_code == 422

    # Patch with IGNORED and valid note -> 200
    ok_patch = client.patch(
        f"/api/alerts/{alert_id}",
        headers=caregiver_a,
        json={"status": "IGNORED", "note": "Bác sĩ hướng dẫn tạm dừng"},
    )
    assert ok_patch.status_code == 200
    patched_data = ok_patch.json()
    assert patched_data["status"] == "IGNORED"
    assert patched_data["note"] == "Bác sĩ hướng dẫn tạm dừng"
    assert patched_data["resolved_at"] is not None

    # Resolve alert directly
    res_alert = client.post(
        f"/api/alerts/{alert_id}/resolve",
        headers=caregiver_a,
        json={"note": "Đã gọi kiểm tra"},
    )
    assert res_alert.status_code == 200
    assert res_alert.json()["status"] == "CHECKED"

    # Verify /api/events returns recorded events
    events_res = client.get("/api/events", headers=caregiver_a)
    assert events_res.status_code == 200
    assert len(events_res.json()) >= 1


def test_security_unauthenticated_and_operator_isolation(tmp_path):
    client = make_client(tmp_path)
    caregiver = login(client, "caregiver-a@example.test")
    operator = login(client, "operator@example.test")

    # Unauthenticated rejected
    assert client.get("/api/schedules").status_code == 401
    assert client.get("/api/doses").status_code == 401
    assert client.get("/api/events").status_code == 401
    assert client.get("/api/alerts").status_code == 401
    assert client.post("/api/simulation/clock", json={"minutes": 1}).status_code == 401

    # Caregiver cannot call operator-only simulation endpoints
    assert client.post("/api/simulation/clock", headers=caregiver, json={"minutes": 1}).status_code == 403
    assert client.post("/api/simulation/advance", headers=caregiver, json={"minutes": 1}).status_code == 403
    assert client.post("/api/simulation/reset", headers=caregiver, json={}).status_code == 403
    assert client.get("/api/simulation/state", headers=caregiver).status_code == 403

    # Negative weight reading rejected
    assert client.post(
        "/api/simulation/events",
        headers=operator,
        json={"slot": 1, "event_type": "WEIGHT_READING", "payload": {"weight_g": -1.5}},
    ).status_code == 422


def test_simulator_is_bound_to_one_patient_and_reset_preserves_other_patient(tmp_path):
    from app.models import Patient, SimulationState
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver_a = login(client, "caregiver-a@example.test")
    caregiver_b = login(client, "caregiver-b@example.test")
    session_factory = client.app.state.session_factory
    with session_factory.begin() as db:
        patient_b = db.scalar(select(Patient).where(Patient.name == "Hồ sơ giả B"))
        schedule_b = db.scalar(select(MedicationSchedule).where(MedicationSchedule.patient_id == patient_b.id))
        other_dose = DoseOccurrence(
            schedule_id=schedule_b.id,
            scheduled_at=__import__("datetime").datetime(2026, 10, 9, 9, 0),
            status="overdue",
        )
        db.add(other_dose)
        db.flush()
        db.add(Alert(
            patient_id=patient_b.id,
            occurrence_id=other_dose.id,
            recipient_id=patient_b.caregiver_id,
            kind="dose_overdue",
            status="PENDING",
            message="Other caregiver alert",
        ))
        db.add(DeviceEvent(
            event_uuid="07a40a5e-1e75-472d-96eb-c70b0517b4b1",
            event_type="LID_OPENED",
            patient_id=patient_b.id,
            slot=2,
            payload={"device_id": "OTHER"},
        ))
    state = client.get("/api/simulation/state", headers=operator).json()
    assert {s["time"] for s in state["active_schedules"]} == {"08:00", "12:00", "20:00"}
    assert client.get("/api/events", headers=caregiver_a).json() == []
    assert len(client.get("/api/events", headers=caregiver_b).json()) == 1
    assert client.post("/api/simulation/advance", headers=operator, json={"minutes": 60}).status_code == 200
    assert client.post("/api/simulation/advance", headers=operator, json={"minutes": 2}).status_code == 200
    with session_factory() as db:
        assert db.scalars(select(DoseOccurrence).where(DoseOccurrence.schedule_id == schedule_b.id)).first() is not None
    response = client.post("/api/simulation/reset", headers=operator, json={"confirm": True})
    assert response.status_code == 200
    with session_factory() as db:
        assert db.scalar(select(DoseOccurrence).where(DoseOccurrence.schedule_id == schedule_b.id)) is not None
        assert db.scalar(select(Alert).where(Alert.patient_id == patient_b.id)) is not None
        assert db.scalar(select(DeviceEvent).where(DeviceEvent.patient_id == patient_b.id)) is not None
    assert len(client.get("/api/alerts", headers=caregiver_b).json()) == 1


def test_history_uses_virtual_date_and_hides_unassigned_events(tmp_path):
    from datetime import datetime
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver = login(client, "caregiver-a@example.test")
    client.post("/api/simulation/events", headers=operator, json={"slot": 1, "event_type": "LID_OPENED"})
    with client.app.state.session_factory.begin() as db:
        db.add(DeviceEvent(
            event_uuid="8d4ff59e-68b2-4452-8f1e-62ab18f19dda",
            event_type="CLOCK_ADVANCED",
            patient_id=None,
            payload={"device_id": "OTHER"},
            created_at=datetime(2026, 10, 9, 8, 0),
        ))
    assert len(client.get("/api/events?date=2026-10-09", headers=caregiver).json()) == 1
    assert client.get("/api/events?date=2026-10-10", headers=caregiver).json() == []
    assert client.get("/api/events?date=not-a-date", headers=caregiver).status_code == 422


def test_event_uuid_cannot_be_reused_with_changed_payload(tmp_path):
    client = make_client(tmp_path)
    operator = login(client, "operator@example.test")
    event = {"event_uuid": "71aa88a2-a619-4112-a883-1166e0c0898a", "slot": 1, "event_type": "LID_OPENED"}
    assert client.post("/api/simulation/events", headers=operator, json=event).status_code == 200
    assert client.post("/api/simulation/events", headers=operator, json=event).json()["idempotent"] is True
    assert client.post("/api/simulation/events", headers=operator, json={**event, "payload": {"extra": "different"}}).status_code == 409
    assert client.post("/api/simulation/reset", headers=operator, json={}).status_code == 422


def test_sqlite_schema_upgrades_legacy_tables_without_deleting_rows(tmp_path):
    import sqlite3
    from app.main import create_app
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE dose_occurrences (id INTEGER PRIMARY KEY, schedule_id INTEGER, scheduled_at DATETIME, confirmed_at DATETIME, status VARCHAR(30))")
        conn.execute("CREATE TABLE device_events (id INTEGER PRIMARY KEY, event_uuid VARCHAR(36), event_type VARCHAR(30), occurrence_id INTEGER, payload JSON, created_at DATETIME)")
        conn.execute("CREATE TABLE alerts (id INTEGER PRIMARY KEY, patient_id INTEGER, occurrence_id INTEGER, kind VARCHAR(40), message VARCHAR(255), created_at DATETIME, resolved_at DATETIME)")
        conn.execute("CREATE TABLE simulation_state (id INTEGER PRIMARY KEY, device_id VARCHAR(30), virtual_clock VARCHAR(40), compartments JSON, updated_at DATETIME)")
    app = create_app(database_url=f"sqlite:///{database}", jwt_secret="testing-secret")
    from sqlalchemy import inspect
    with app.state.engine.connect() as conn:
        db = inspect(conn)
        assert {"deadline_at", "reminder_count"} <= {c["name"] for c in db.get_columns("dose_occurrences")}
        assert {"patient_id", "slot", "device_id", "occurred_at"} <= {c["name"] for c in db.get_columns("device_events")}
        assert {"recipient_id", "note", "status"} <= {c["name"] for c in db.get_columns("alerts")}
        assert "patient_id" in {c["name"] for c in db.get_columns("simulation_state")}
