from sqlalchemy import func, inspect, select
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import DeviceEvent
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
