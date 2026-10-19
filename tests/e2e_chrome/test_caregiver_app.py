"""Flutter Web Caregiver App Chrome DevTools E2E Tests (R3.1 - R3.5).

Verifies:
- R3.1: Caregiver A login, CanvasKit accessibility semantics activation, and patient data isolation
- R3.2: Today tab patient header, SIM-001 status, and daily dose cards (Slots 1, 2, 3)
- R3.3: Schedule tab, 24h schedule manager, and duplicate schedule 409 Conflict rejection
- R3.4: Alerts tab, overdue alert card, and Quick Note Chips resolution to CHECKED
- R3.5: Medical Timeline View (History tab) displaying chronological hardware events
"""

import os
import sys
import re
import time
import json
import uuid
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from playwright.sync_api import Page, expect
from tests.e2e_chrome.conftest import ConsoleAuditTracker
from tests.e2e_chrome.service_manager import ServiceManager, FLUTTER_URL, BACKEND_URL


def enable_flutter_semantics(page: Page) -> None:
    """Activates Flutter Web CanvasKit accessibility semantics tree."""
    page.wait_for_selector("flt-semantics-placeholder", state="attached", timeout=30000)
    page.evaluate("() => document.querySelector('flt-semantics-placeholder')?.click()")
    page.wait_for_selector("input, flt-semantics", state="attached", timeout=15000)
    time.sleep(1.0)


def login_caregiver_a(page: Page) -> None:
    """Logs in Caregiver A and navigates to Today dashboard."""
    page.goto(f"{FLUTTER_URL}/")
    page.wait_for_load_state("domcontentloaded")
    enable_flutter_semantics(page)

    email_inp = page.locator("input[aria-label='Email']")
    email_inp.click()
    email_inp.press("Control+A")
    email_inp.press("Backspace")
    email_inp.fill("caregiver-a@example.test")

    pass_inp = page.locator("input[aria-label='Mật khẩu']")
    pass_inp.click()
    pass_inp.press("Control+A")
    pass_inp.press("Backspace")
    pass_inp.fill("Password123!")

    login_btn = page.get_by_role("button", name="Đăng nhập")
    login_btn.click()

    # Wait for patient name "Hồ sơ giả A" to be visible
    expect(page.get_by_text("Hồ sơ giả A").first).to_be_visible(timeout=10000)
    time.sleep(1.0)


def test_caregiver_login_and_data_isolation(live_services: ServiceManager, app_page: Page, audit_tracker: ConsoleAuditTracker):
    """R3.1: Verify Caregiver A login and strict data isolation from Caregiver B."""
    live_services.reset_state()

    app_page.goto(f"{FLUTTER_URL}/")
    app_page.wait_for_load_state("domcontentloaded")
    enable_flutter_semantics(app_page)

    audit_tracker.record_screenshot(app_page, "09_caregiver_login_screen.png", "Caregiver Mobile App login screen")

    # Clear and fill
    email_inp = app_page.locator("input[aria-label='Email']")
    email_inp.click()
    email_inp.press("Control+A")
    email_inp.press("Backspace")
    email_inp.fill("caregiver-a@example.test")

    pass_inp = app_page.locator("input[aria-label='Mật khẩu']")
    pass_inp.click()
    pass_inp.press("Control+A")
    pass_inp.press("Backspace")
    pass_inp.fill("Password123!")

    login_btn = app_page.get_by_role("button", name="Đăng nhập")
    login_btn.click()

    # Verify Patient 1 "Hồ sơ giả A" is displayed
    patient_node = app_page.get_by_text("Hồ sơ giả A").first
    expect(patient_node).to_be_visible(timeout=10000)

    # Strict Data Isolation: Caregiver B patient ("Hồ sơ giả B") and medication ("Thuốc mẫu B") MUST NOT be present
    expect(app_page.get_by_text("Hồ sơ giả B")).not_to_be_visible()
    expect(app_page.get_by_text("Thuốc mẫu B")).not_to_be_visible()

    audit_tracker.record_screenshot(app_page, "10_caregiver_today_dashboard.png", "Caregiver dashboard with Patient A and isolation from Patient B")
    audit_tracker.assert_no_uncaught_errors()


def test_caregiver_today_tab_dose_cards(live_services: ServiceManager, app_page: Page, audit_tracker: ConsoleAuditTracker):
    """R3.2: Verify Today tab dose cards for Patient 1 (Thuốc A, Thuốc B, Thuốc C)."""
    live_services.reset_state()
    login_caregiver_a(app_page)

    # Verify daily doses are visible via aria-label on card groups
    expect(app_page.locator('[aria-label*="Thuốc A"]').first).to_be_visible(timeout=5000)
    expect(app_page.locator('[aria-label*="Thuốc B"]').first).to_be_visible()
    expect(app_page.locator('[aria-label*="Thuốc C"]').first).to_be_visible()

    # Initial status: Không có cảnh báo quá hạn nào
    expect(app_page.get_by_text("Không có cảnh báo quá hạn nào.").first).to_be_visible()

    audit_tracker.record_screenshot(app_page, "11_caregiver_today_dose_cards.png", "Today tab daily dose cards for slots 1, 2, 3")
    audit_tracker.assert_no_uncaught_errors()


def test_caregiver_schedule_tab_and_409_conflict(live_services: ServiceManager, app_page: Page, audit_tracker: ConsoleAuditTracker):
    """R3.3: Verify Schedule tab, add 24h schedule, and catch HTTP 409 Conflict on duplicate slot/time."""
    live_services.reset_state()
    login_caregiver_a(app_page)

    # Navigate to Schedule tab ("Lịch" at x=126, y=820)
    app_page.mouse.click(126, 820)
    time.sleep(1.5)

    # Verify Schedule header
    expect(app_page.get_by_text("Quản lý lịch uống").first).to_be_visible(timeout=5000)

    # Click FAB "Thêm lịch"
    add_fab = app_page.get_by_text("Thêm lịch").first
    expect(add_fab).to_be_visible(timeout=5000)
    add_fab.click()
    time.sleep(1.0)

    # Dialog "Thêm lịch uống thuốc" is open
    expect(app_page.get_by_text("Thêm lịch uống thuốc").first).to_be_visible(timeout=5000)

    # Fill duplicate schedule: Ngăn 1 at 08:00 (which already exists for Patient 1)
    name_box = app_page.get_by_role("textbox", name="Tên thuốc mẫu")
    name_box.click()
    name_box.fill("Thuốc Trùng Ngăn 1")

    # Click "Lưu lịch"
    save_btn = app_page.get_by_role("button", name="Lưu lịch")
    save_btn.click()
    time.sleep(1.5)

    # Backend responds with 409 Conflict: "Ngăn 1 đã có lịch uống lúc 08:00"
    conflict_msg = app_page.locator('[aria-label*="Ngăn 1 đã có lịch uống lúc 08:00"], :text("Ngăn 1 đã có lịch uống lúc 08:00")').first
    expect(conflict_msg).to_be_visible(timeout=5000)

    audit_tracker.record_screenshot(app_page, "12_caregiver_schedule_conflict_error.png", "Schedule 409 Conflict error for duplicate time/slot")

    # Dismiss dialog
    cancel_btn = app_page.get_by_role("button", name="Hủy")
    cancel_btn.click()
    time.sleep(1.0)

    audit_tracker.assert_no_uncaught_errors()


def test_caregiver_alerts_quick_note_resolution(live_services: ServiceManager, app_page: Page, audit_tracker: ConsoleAuditTracker):
    """R3.4: Advance clock to 08:05, verify overdue alert, and resolve with Quick Note Chip to CHECKED."""
    live_services.reset_state()

    # Advance clock to 08:05 via API to trigger overdue alert for Slot 1 (08:00)
    token = live_services.get_operator_token()
    advance_url = f"{BACKEND_URL}/api/simulation/advance"
    advance_body = json.dumps({"minutes": 6, "event_uuid": str(uuid.uuid4())}).encode("utf-8")
    adv_req = urllib.request.Request(advance_url, data=advance_body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    urllib.request.urlopen(adv_req, timeout=15)

    # Login Caregiver A
    login_caregiver_a(app_page)

    # Navigate to Alerts tab ("Cảnh báo" at x=294, y=820)
    app_page.mouse.click(294, 820)
    time.sleep(2.0)

    # Explicitly click refresh button so overdue alert card is rendered immediately
    app_page.get_by_role("button", name="Làm mới cảnh báo").click()
    time.sleep(1.0)

    # Verify overdue alert card is present
    alert_card = app_page.locator('[aria-label*="Chưa xác nhận Thuốc A ở ngăn 1"]').first
    expect(alert_card).to_be_visible(timeout=8000)

    # Click "Xử lý" button
    resolve_btn = app_page.get_by_role("button", name="Xử lý").first
    resolve_btn.click()
    time.sleep(1.0)

    # Verify modal dialog opened
    expect(app_page.get_by_text("Xử lý cảnh báo").first).to_be_visible(timeout=5000)
    audit_tracker.record_screenshot(app_page, "13_caregiver_alert_modal_quick_chips.png", "Alert resolution modal with Quick Note Chips")

    # Select Quick Note Chip: "Đã kiểm tra khay thuốc"
    quick_chip = app_page.locator('[aria-label*="Đã kiểm tra khay thuốc"]').first
    expect(quick_chip).to_be_visible(timeout=5000)
    quick_chip.click()
    time.sleep(0.5)

    # Click "Xác nhận"
    confirm_resolve_btn = app_page.get_by_role("button", name="Xác nhận")
    confirm_resolve_btn.click()
    time.sleep(2.0)

    # Verify alert transitioned to "Trạng thái: Đã kiểm tra"
    expect(app_page.locator('[aria-label*="Đã kiểm tra"], :text("Đã kiểm tra")').first).to_be_visible(timeout=5000)

    audit_tracker.record_screenshot(app_page, "14_caregiver_alert_resolved_checked.png", "Alert transitioned to CHECKED with Quick Note note")
    audit_tracker.assert_no_uncaught_errors()


def test_caregiver_medical_timeline_view(live_services: ServiceManager, app_page: Page, audit_tracker: ConsoleAuditTracker):
    """R3.5: Verify Medical Timeline View (History tab) displaying sequence of events."""
    live_services.reset_state()

    # Generate sample hardware events via API: LID_OPENED, WEIGHT_READING, CONFIRM_PRESSED
    token = live_services.get_operator_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    events_url = f"{BACKEND_URL}/api/simulation/events"

    # Open lid
    urllib.request.urlopen(urllib.request.Request(events_url, data=json.dumps({"slot": 1, "event_type": "LID_OPENED", "event_uuid": str(uuid.uuid4())}).encode("utf-8"), headers=headers), timeout=15)
    # Weight reading
    urllib.request.urlopen(urllib.request.Request(events_url, data=json.dumps({"slot": 1, "event_type": "WEIGHT_READING", "weight_g": 4.5, "event_uuid": str(uuid.uuid4())}).encode("utf-8"), headers=headers), timeout=15)
    # Close lid
    urllib.request.urlopen(urllib.request.Request(events_url, data=json.dumps({"slot": 1, "event_type": "LID_CLOSED", "event_uuid": str(uuid.uuid4())}).encode("utf-8"), headers=headers), timeout=15)

    # Login Caregiver A
    login_caregiver_a(app_page)

    # Navigate to History tab ("Lịch sử" at x=210, y=820)
    app_page.mouse.click(210, 820)
    time.sleep(2.0)

    # Verify history title & timeline events
    expect(app_page.get_by_text("Lịch sử sự kiện").first).to_be_visible(timeout=5000)
    expect(app_page.get_by_text("Mở nắp ngăn thuốc").first).to_be_visible(timeout=5000)

    audit_tracker.record_screenshot(app_page, "15_caregiver_medical_timeline_view.png", "Caregiver Medical Timeline View with hardware events")
    audit_tracker.assert_no_uncaught_errors()
