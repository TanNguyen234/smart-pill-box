"""Regression tests for simulated vs automatic Vietnamese realtime reminders."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app.models import Alert, DoseOccurrence, MedicationSchedule, SimulationState
from app.realtime import tick_realtime
from app.seed import seed_demo

VN_TZ = timezone(timedelta(hours=7))


def client_with_seed(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'two_clocks.sqlite3'}", jwt_secret="tests-only-secret")
    seed_demo(app.state.session_factory, "demo-password")
    return TestClient(app)


def login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "demo-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_realtime_switch_is_operator_only_and_simulation_resumes(tmp_path):
    client = client_with_seed(tmp_path)
    caregiver = login(client, "caregiver-a@example.test")
    operator = login(client, "operator@example.test")
    fixed = datetime(2026, 10, 20, 7, 59, 9, tzinfo=VN_TZ)
    client.app.state.now_provider = lambda: fixed

    assert client.post("/api/simulation/mode", json={"clock_mode": "REALTIME"}).status_code == 401
    assert client.post("/api/simulation/mode", headers=caregiver, json={"clock_mode": "REALTIME"}).status_code == 403
    assert client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "invalid"}).status_code == 422

    first = client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "REALTIME"})
    assert first.status_code == 200
    assert first.json()["clock_mode"] == "REALTIME"
    assert first.json()["virtual_clock"].startswith("2026-10-20T07:59")
    assert client.post("/api/simulation/advance", headers=operator, json={"minutes": 1}).status_code == 409
    assert client.post("/api/simulation/reset", headers=operator, json={"confirmation": "RESET_DEMO"}).status_code == 409

    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=0)) is True
    state = client.get("/api/simulation/state", headers=operator).json()
    assert state["compartments"][0]["led"] == "Bật"
    assert state["active_occurrences"][0]["status"] == "pending"
    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=0, second=27)) is True
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DoseOccurrence)) == 1

    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=2)) is True
    state = client.get("/api/simulation/state", headers=operator).json()
    assert state["active_occurrences"][0]["status"] == "reminded"

    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=5)) is True
    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=5, second=30)) is True
    with client.app.state.session_factory() as db:
        doses = db.scalars(select(DoseOccurrence)).all()
        assert len(doses) == 1
        assert doses[0].clock_mode == "REALTIME"
        assert doses[0].reminder_count == 2
        assert doses[0].status == "overdue"
        assert db.scalar(select(func.count()).select_from(Alert)) == 1

    back = client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "SIMULATION"})
    assert back.status_code == 200
    assert back.json()["clock_mode"] == "SIMULATION"
    assert back.json()["virtual_clock"] == "2026-10-09T07:59:00+07:00"
    assert back.json()["active_occurrences"] == []
    assert tick_realtime(client.app, now=fixed.replace(hour=8, minute=6)) is False
    # Old demo mode still works without replaying realtime occurrences.
    simulated = client.post("/api/simulation/advance", headers=operator, json={"minutes": 1})
    assert simulated.status_code == 200
    assert simulated.json()["active_occurrences"][0]["status"] == "pending"
    with client.app.state.session_factory() as db:
        assert {d.clock_mode for d in db.scalars(select(DoseOccurrence)).all()} == {"SIMULATION", "REALTIME"}


def test_realtime_checks_new_schedules_within_current_minute(tmp_path):
    client = client_with_seed(tmp_path)
    operator = login(client, "operator@example.test")
    caregiver = login(client, "caregiver-a@example.test")
    fixed = datetime(2026, 10, 20, 10, 31, 10, tzinfo=VN_TZ)
    client.app.state.now_provider = lambda: fixed
    assert client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "REALTIME"}).status_code == 200
    with client.app.state.session_factory() as db:
        state = db.scalar(select(SimulationState).where(SimulationState.device_id == "SIM-001"))
        assert state.clock_mode == "REALTIME"
        patient_id = state.patient_id

    added = client.post("/api/schedules", headers=caregiver, json={
        "patient_id": patient_id, "medication_name": "Thuốc vừa thêm", "slot": 1, "time": "10:31", "active": True
    })
    assert added.status_code == 201
    assert tick_realtime(client.app, now=fixed.replace(second=20)) is True
    with client.app.state.session_factory() as db:
        row = db.scalar(select(DoseOccurrence).where(DoseOccurrence.schedule_id == added.json()["id"]))
        assert row is not None
        assert row.clock_mode == "REALTIME"
        assert row.status == "pending"


def test_realtime_mode_and_cursor_survive_backend_restart(tmp_path):
    client = client_with_seed(tmp_path)
    operator = login(client, "operator@example.test")
    when = datetime(2026, 10, 20, 7, 59, tzinfo=VN_TZ)
    client.app.state.now_provider = lambda: when
    assert client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "REALTIME"}).status_code == 200
    tick_realtime(client.app, now=when.replace(hour=8, minute=0))
    database_url = str(client.app.state.engine.url)
    restarted = create_app(database_url=database_url, jwt_secret="tests-only-secret")
    restarted.state.now_provider = lambda: when.replace(hour=8, minute=5)
    with TestClient(restarted) as after_restart:
        assert restarted.state.realtime_worker is not None
        operator2 = login(after_restart, "operator@example.test")
        assert after_restart.get("/api/simulation/state", headers=operator2).json()["clock_mode"] == "REALTIME"
        assert tick_realtime(restarted, now=when.replace(hour=8, minute=5)) is True
        assert after_restart.get("/api/alerts", headers=login(after_restart, "caregiver-a@example.test")).json()
        with restarted.state.session_factory() as db:
            assert db.scalar(select(func.count()).select_from(Alert)) == 1
    assert restarted.state.realtime_worker.done()


def test_realtime_same_minute_retries_do_not_duplicate_reminders(tmp_path):
    client = client_with_seed(tmp_path)
    operator = login(client, "operator@example.test")
    when = datetime(2026, 10, 20, 7, 59, tzinfo=VN_TZ)
    client.app.state.now_provider = lambda: when
    client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "REALTIME"})
    for seconds in [0, 5, 15, 40]:
        tick_realtime(client.app, now=when.replace(hour=8, minute=0, second=seconds))
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DoseOccurrence)) == 1


def test_lifespan_worker_triggers_a_reminder_without_any_advance_request(tmp_path):
    import time
    client = client_with_seed(tmp_path)
    operator = login(client, "operator@example.test")
    now = datetime(2026, 10, 20, 7, 59, tzinfo=VN_TZ)
    client.app.state.now_provider = lambda: now
    assert client.post("/api/simulation/mode", headers=operator, json={"clock_mode": "REALTIME"}).status_code == 200
    # No calls to /api/simulation/advance or explicit tick_realtime.
    client.app.state.now_provider = lambda: now.replace(hour=8, minute=0, second=5)
    with TestClient(client.app) as running:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = running.get("/api/simulation/state", headers=operator).json()
            if state["active_occurrences"]:
                break
            time.sleep(0.05)
        assert state["active_occurrences"][0]["status"] == "pending"
        with client.app.state.session_factory() as db:
            assert db.scalar(select(func.count()).select_from(DoseOccurrence)) == 1
