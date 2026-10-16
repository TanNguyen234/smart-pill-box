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
        "/api/simulation/reset", headers=operator, json={"event_uuid": reset_event_uuid}
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
        "/api/simulation/reset", headers=operator, json={"event_uuid": reset_event_uuid}
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
