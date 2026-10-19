"""Adversarial Verification Suite for Smart Pill Box E2E Testing.

Executed by challenger_e2e_1 to empirically verify:
1. Load cell threshold logic (>=0.3g vs <0.3g, boundary tests at 0.29g and 0.30g, closed-lid rejection).
2. Schedule 409 Conflict detection and multi-tenant authorization boundaries (403 cross-tenant isolation).
3. Minute-by-minute virtual clock state machine progression (07:59 -> 08:00 -> 08:01 -> 08:02 -> 08:04 -> 08:05).
4. Real Google Chrome binary CDP connection and runtime inspection.
"""

import sys
import os
import json
import uuid
import time
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from tests.e2e_chrome.service_manager import ServiceManager, BACKEND_URL, SIMULATOR_URL, FLUTTER_URL


def http_req(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"detail": content}
        return e.code, parsed


def get_tokens():
    _, op_res = http_req(f"{BACKEND_URL}/api/auth/login", "POST", {"email": "operator@example.test", "password": "Password123!"})
    _, a_res = http_req(f"{BACKEND_URL}/api/auth/login", "POST", {"email": "caregiver-a@example.test", "password": "Password123!"})
    _, b_res = http_req(f"{BACKEND_URL}/api/auth/login", "POST", {"email": "caregiver-b@example.test", "password": "Password123!"})
    return op_res["access_token"], a_res["access_token"], b_res["access_token"]


def reset_backend(op_token):
    code, state = http_req(f"{BACKEND_URL}/api/simulation/reset", "POST", {"confirm": True, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200, f"Reset failed: {state}"
    return state


def run_adversarial_loadcell_tests(op_token):
    print("\n--- [ADVERSARIAL 1] Load Cell Boundary & Jitter Oracle ---")
    reset_backend(op_token)

    # 1. Attempt weight reading with lid CLOSED -> MUST return 409
    code, res = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 4.5, "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 409, f"Expected 409 for closed lid weight reading, got {code}: {res}"
    print("  [PASS] Closed lid weight reading rejected with HTTP 409:", res.get("detail"))

    # Open lid
    code, _ = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "LID_OPENED", "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 200

    # Baseline weight is 5.0g, pill count is 10
    # 2. Test boundary: Drop 0.1g (noise: 5.0 -> 4.9g) -> count MUST remain 10
    code, state = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 4.9, "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 200
    comp1 = state["compartments"][0]
    assert comp1["pill_count"] == 10, f"Expected pill count 10 on 0.1g drop, got {comp1['pill_count']}"
    assert comp1["weight_grams"] == 4.9
    print("  [PASS] Drop 0.1g (<0.3g): weight=4.9g, pill_count remains 10")

    # 3. Test boundary: Drop 0.29g (from 4.9 to 4.61g) -> drop is 0.29 < 0.3g -> count MUST remain 10
    code, state = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 4.61, "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 200
    comp1 = state["compartments"][0]
    assert comp1["pill_count"] == 10, f"Expected pill count 10 on 0.29g drop, got {comp1['pill_count']}"
    assert comp1["weight_grams"] == 4.6
    print("  [PASS] Boundary Drop 0.29g (<0.3g threshold): weight=4.6g, pill_count strictly remains 10")

    # 4. Test exact threshold: Drop 0.30g (from 4.6 to 4.3g) -> drop is 0.30 >= 0.3g -> count MUST decrement to 9
    code, state = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 4.3, "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 200
    comp1 = state["compartments"][0]
    assert comp1["pill_count"] == 9, f"Expected pill count 9 on 0.30g drop, got {comp1['pill_count']}"
    assert comp1["weight_grams"] == 4.3
    print("  [PASS] Exact Threshold Drop 0.30g (>=0.3g threshold): weight=4.3g, pill_count decremented to 9")

    # 5. Test standard pill dispense: Drop 0.50g (from 4.3 to 3.8g) -> count MUST decrement to 8
    code, state = http_req(
        f"{BACKEND_URL}/api/simulation/events",
        "POST",
        {"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 3.8, "event_uuid": str(uuid.uuid4())},
        op_token,
    )
    assert code == 200
    comp1 = state["compartments"][0]
    assert comp1["pill_count"] == 8, f"Expected pill count 8 on 0.50g drop, got {comp1['pill_count']}"
    assert comp1["weight_grams"] == 3.8
    print("  [PASS] Pill Dispense Drop 0.50g: weight=3.8g, pill_count decremented to 8")


def run_adversarial_conflict_and_isolation_tests(op_token, a_token, b_token):
    print("\n--- [ADVERSARIAL 2] Schedule 409 Conflict & Multi-Tenant Isolation Oracle ---")
    reset_backend(op_token)

    # 1. Caregiver A checks patients
    code, a_patients = http_req(f"{BACKEND_URL}/api/patients", "GET", token=a_token)
    assert code == 200
    assert len(a_patients) == 1
    a_patient = a_patients[0]
    assert a_patient["name"] == "Hồ sơ giả A"
    print(f"  [PASS] Caregiver A sees only own patient: {a_patient['name']} (ID {a_patient['id']})")

    # 2. Caregiver B checks patients
    code, b_patients = http_req(f"{BACKEND_URL}/api/patients", "GET", token=b_token)
    assert code == 200
    assert len(b_patients) == 1
    b_patient = b_patients[0]
    assert b_patient["name"] == "Hồ sơ giả B"
    print(f"  [PASS] Caregiver B sees only own patient: {b_patient['name']} (ID {b_patient['id']})")

    # 3. Duplicate schedule on Caregiver A (Patient A, slot 1, 08:00 already exists) -> MUST return 409
    code, res = http_req(
        f"{BACKEND_URL}/api/schedules",
        "POST",
        {"patient_id": a_patient["id"], "medication_name": "Thuốc Trùng Ngăn 1", "slot": 1, "time": "08:00", "active": True},
        a_token,
    )
    assert code == 409, f"Expected 409 for duplicate schedule, got {code}: {res}"
    assert "Ngăn 1 đã có lịch uống lúc 08:00" in res.get("detail", "")
    print(f"  [PASS] Duplicate schedule strictly rejected with HTTP 409: '{res.get('detail')}'")

    # 4. Different slot, same time: test creating and deactivating schedule
    test_time = "23:50"
    code, res = http_req(
        f"{BACKEND_URL}/api/schedules",
        "POST",
        {"patient_id": a_patient["id"], "medication_name": "Thuốc Thử Nghiệm", "slot": 2, "time": test_time, "active": True},
        a_token,
    )
    assert code == 201, f"Expected 201 for different slot, got {code}: {res}"
    created_id = res.get("id")
    print("  [PASS] Distinct slot at same time created successfully (HTTP 201)")

    # Deactivate test schedule immediately to maintain clean state
    if created_id:
        http_req(f"{BACKEND_URL}/api/schedules/{created_id}", "PATCH", {"active": False}, a_token)

    # 5. Cross-tenant tampering: Caregiver A attempts to create schedule for Patient B -> MUST return 403 Forbidden
    code, res = http_req(
        f"{BACKEND_URL}/api/schedules",
        "POST",
        {"patient_id": b_patient["id"], "medication_name": "Thuốc Đột Nhập", "slot": 1, "time": "15:00", "active": True},
        a_token,
    )
    assert code == 403, f"Expected 403 for cross-tenant schedule creation, got {code}: {res}"
    print(f"  [PASS] Cross-tenant tampering strictly rejected with HTTP 403: '{res.get('detail')}'")

    # 6. Cross-tenant schedule retrieval: Caregiver A only gets Patient A schedules
    code, a_schedules = http_req(f"{BACKEND_URL}/api/schedules", "GET", token=a_token)
    assert code == 200
    for s in a_schedules:
        assert s["patient_id"] == a_patient["id"]
        assert "Thuốc mẫu B" not in s["medication_name"]
    print(f"  [PASS] Caregiver A schedules query strictly isolated ({len(a_schedules)} schedules, 0 from Caregiver B)")


def run_adversarial_clock_timeline_tests(op_token, a_token):
    print("\n--- [ADVERSARIAL 3] Minute-by-Minute Virtual Clock State Machine Oracle ---")
    reset_backend(op_token)

    # Find schedule_id for Thuốc A (slot 1)
    code, a_schedules = http_req(f"{BACKEND_URL}/api/schedules", "GET", token=a_token)
    assert code == 200
    slot1_sched = next(s for s in a_schedules if s["slot"] == 1 and s["time"] == "08:00")
    slot1_id = slot1_sched["id"]

    # Helper to get dose status for Thuốc A (slot 1)
    def get_slot1_status():
        code, doses = http_req(f"{BACKEND_URL}/api/doses", "GET", token=a_token)
        assert code == 200
        for d in doses:
            if d["schedule_id"] == slot1_id:
                return d["status"], d["reminder_count"]
        return None, None

    # Step 0: 07:59:00 -> Standby (no dose occurrence generated yet for 08:00)
    status, reminder_count = get_slot1_status()
    print(f"  [07:59:00] Initial status: {status}, reminder_count: {reminder_count}")
    assert status is None, f"Expected no dose occurrence at 07:59:00, got {status}"

    # Step 1: Advance +1m to 08:00:00 -> Due time reached!
    code, _ = http_req(f"{BACKEND_URL}/api/simulation/advance", "POST", {"minutes": 1, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200
    status, reminder_count = get_slot1_status()
    print(f"  [08:00:00] Status: {status}, reminder_count: {reminder_count}")
    assert status == "pending", f"Expected 'pending' at 08:00:00, got {status}"
    assert reminder_count == 1, f"Expected reminder_count 1 at 08:00:00, got {reminder_count}"

    # Step 2: Advance +1m to 08:01:00 -> 1 min elapsed, still pending reminder 1
    code, _ = http_req(f"{BACKEND_URL}/api/simulation/advance", "POST", {"minutes": 1, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200
    status, reminder_count = get_slot1_status()
    print(f"  [08:01:00] Status: {status}, reminder_count: {reminder_count}")
    assert status == "pending", f"Expected 'pending' at 08:01:00, got {status}"
    assert reminder_count == 1, f"Expected reminder_count 1 at 08:01:00, got {reminder_count}"

    # Step 3: Advance +1m to 08:02:00 -> 2 min elapsed, transitions to 'reminded' (reminder 2)
    code, _ = http_req(f"{BACKEND_URL}/api/simulation/advance", "POST", {"minutes": 1, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200
    status, reminder_count = get_slot1_status()
    print(f"  [08:02:00] Status: {status}, reminder_count: {reminder_count}")
    assert status == "reminded", f"Expected 'reminded' at 08:02:00, got {status}"
    assert reminder_count == 2, f"Expected reminder_count 2 at 08:02:00, got {reminder_count}"

    # Step 4: Advance +2m to 08:04:00 -> 4 min elapsed, still reminded
    code, _ = http_req(f"{BACKEND_URL}/api/simulation/advance", "POST", {"minutes": 2, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200
    status, reminder_count = get_slot1_status()
    print(f"  [08:04:00] Status: {status}, reminder_count: {reminder_count}")
    assert status == "reminded", f"Expected 'reminded' at 08:04:00, got {status}"
    assert reminder_count == 2

    # Step 5: Advance +1m to 08:05:00 -> 5 min elapsed, transitions to 'overdue'!
    code, _ = http_req(f"{BACKEND_URL}/api/simulation/advance", "POST", {"minutes": 1, "event_uuid": str(uuid.uuid4())}, op_token)
    assert code == 200
    status, reminder_count = get_slot1_status()
    print(f"  [08:05:00] Status: {status}, reminder_count: {reminder_count}")
    assert status == "overdue", f"Expected 'overdue' at 08:05:00, got {status}"

    # Check alert was created
    code, alerts = http_req(f"{BACKEND_URL}/api/alerts", "GET", token=a_token)
    assert code == 200
    overdue_alerts = [a for a in alerts if a["kind"] == "dose_overdue"]
    assert len(overdue_alerts) >= 1, f"Expected overdue alert, got {alerts}"
    print(f"  [08:05:00] Overdue alert created: '{overdue_alerts[0]['message']}'")


def run_adversarial_chrome_binary_tests():
    print("\n--- [ADVERSARIAL 4] Real Google Chrome Binary & CDP Connection Verification ---")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--force-renderer-accessibility", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        version = browser.version
        print(f"  [Browser Launched] Browser Version: {version}")
        assert "155." in version or "Chrome" in version, f"Unexpected browser version: {version}"

        context = browser.new_context()
        page = context.new_page()

        # Connect CDP session directly
        cdp = context.new_cdp_session(page)
        cdp_version_info = cdp.send("Browser.getVersion")
        print(f"  [CDP Info] Product: {cdp_version_info.get('product')}")
        print(f"  [CDP Info] UserAgent: {cdp_version_info.get('userAgent')}")
        print(f"  [CDP Info] ProtocolVersion: {cdp_version_info.get('protocolVersion')}")

        assert "Chrome" in cdp_version_info.get("product", ""), "Must be real Google Chrome"
        browser.close()
    print("  [PASS] Real Google Chrome CDP connection verified!")


def main():
    print("=" * 70)
    print(" ADVERSARIAL CHALLENGE EXECUTION - SMART PILL BOX E2E SUITE")
    print("=" * 70)

    manager = ServiceManager()
    manager.start_all()
    try:
        op_token, a_token, b_token = get_tokens()
        run_adversarial_loadcell_tests(op_token)
        run_adversarial_conflict_and_isolation_tests(op_token, a_token, b_token)
        run_adversarial_clock_timeline_tests(op_token, a_token)
        run_adversarial_chrome_binary_tests()
        print("\n" + "=" * 70)
        print(" ALL ADVERSARIAL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
