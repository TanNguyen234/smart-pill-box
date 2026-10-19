"""Cross-UI Medical Timeline Synchronized Chrome DevTools E2E Tests (R4.1 - R4.5).

Verifies the end-to-end synchronized medication lifecycle across:
- Web Simulator (Desktop Viewport 1280x800 on http://127.0.0.1:5173)
- Flutter Web Caregiver App (Mobile Viewport 420x860 on http://127.0.0.1:8080)
- FastAPI Backend (http://127.0.0.1:8000)

Timeline:
- R4.1 (07:59): Baseline standby, Thuốc A scheduled at 08:00 ('Chưa đến giờ')
- R4.2 (08:00): Advance +1m -> First alarm: Simulator LED/buzzer active, Caregiver App shows 'Đang nhắc uống'
- R4.3 (08:02): Advance +2m -> Second reminder: Caregiver App shows 'Đã nhắc lại (2 phút)'
- R4.4 (08:05): Advance +3m -> Overdue alert: Caregiver App shows 'Quá hạn, chưa xác nhận' and Alert card
- R4.5 (Pill Taken): Simulator Lid opened -> Dispense 0.5g -> Lid closed -> Confirm pressed -> Caregiver App resolved
"""

import sys
import re
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from playwright.sync_api import Page, expect
from tests.e2e_chrome.conftest import ConsoleAuditTracker
from tests.e2e_chrome.service_manager import ServiceManager, SIMULATOR_URL, FLUTTER_URL


def setup_simulator_page(page: Page) -> None:
    """Navigates to Web Simulator and logs in Operator."""
    page.goto(f"{SIMULATOR_URL}/")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("#email", timeout=10000)
    page.locator("#email").fill("operator@example.test")
    page.locator("#password").fill("Password123!")
    page.locator("button.login-button").click()
    expect(page.locator(".user-chip")).to_be_visible(timeout=5000)


def setup_caregiver_page(page: Page) -> None:
    """Navigates to Flutter Web Caregiver App, enables semantics, and logs in Caregiver A."""
    page.goto(f"{FLUTTER_URL}/")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("flt-semantics-placeholder", state="attached", timeout=30000)
    page.evaluate("() => document.querySelector('flt-semantics-placeholder')?.click()")
    page.wait_for_selector("input, flt-semantics", state="attached", timeout=15000)
    time.sleep(1.0)

    email_inp = page.locator("input[aria-label='Email']")
    email_inp.click()
    email_inp.fill("caregiver-a@example.test")

    pass_inp = page.locator("input[aria-label='Mật khẩu']")
    pass_inp.click()
    pass_inp.fill("Password123!")

    page.get_by_role("button", name="Đăng nhập").click()
    expect(page.get_by_text("Hồ sơ giả A").first).to_be_visible(timeout=10000)
    time.sleep(1.0)


def test_cross_ui_synchronized_timeline(
    live_services: ServiceManager,
    sim_page: Page,
    app_page: Page,
    audit_tracker: ConsoleAuditTracker,
):
    """Executes the full 07:59 -> 08:00 -> 08:02 -> 08:05 -> Dispense Cross-UI test scenario."""
    # 0. Clean reset
    live_services.reset_state()

    # 1. Initialize both UIs
    setup_simulator_page(sim_page)
    setup_caregiver_page(app_page)

    # -------------------------------------------------------------------------
    # R4.1: Standby baseline at 07:59:00
    # -------------------------------------------------------------------------
    # Check Web Simulator OLED clock
    oled_clock = sim_page.locator(".clock-card strong")
    expect(oled_clock).to_contain_text("07:59:00", timeout=5000)

    # Check Caregiver App Today tab: Slot 1 Thuốc A says "Chưa đến giờ"
    thuoc_a_card = app_page.locator('[aria-label*="Thuốc A"]').first
    expect(thuoc_a_card).to_be_visible(timeout=5000)
    expect(thuoc_a_card).to_have_attribute("aria-label", re.compile(r"Chưa đến giờ"))

    audit_tracker.record_screenshot(app_page, "16_cross_0759_standby.png", "Standby baseline at 07:59:00 - Slot 1 standby")

    # -------------------------------------------------------------------------
    # R4.2: First Alarm at 08:00:00 (+1m)
    # -------------------------------------------------------------------------
    # In Web Simulator: click "+1 phút" button
    plus_1m_btn = sim_page.locator(".clock-buttons button").first
    plus_1m_btn.click()

    # Verify Web Simulator: OLED shows 08:00:00, LED active, Buzzer active, Confirm button visible
    expect(oled_clock).to_contain_text("08:00:00", timeout=5000)
    slot1_sim = sim_page.locator(".compartment-card.slot-1")
    expect(slot1_sim.locator(".led-lens")).to_have_class(re.compile(r"led-active"), timeout=5000)
    expect(slot1_sim.locator(".led-text")).to_have_text("LED BẬT")
    expect(slot1_sim.locator(".buzzer-line")).to_have_class(re.compile(r"buzzer-active"))
    expect(slot1_sim.locator("button.confirm-button")).to_be_visible(timeout=5000)

    audit_tracker.record_screenshot(sim_page, "17_cross_0800_alarm_led_buzzer.png", "Alarm triggered at 08:00:00 - LED pulse and Buzzer active")

    # In Caregiver App: reload data and verify status transitioned to "Đang nhắc uống"
    app_page.get_by_role("button", name="Tải lại dữ liệu").click()
    time.sleep(1.5)
    expect(app_page.locator('[aria-label*="Thuốc A"][aria-label*="Đang nhắc uống"]').first).to_be_visible(timeout=8000)

    # -------------------------------------------------------------------------
    # R4.3: Snooze / Second Reminder at 08:02:00 (+2m)
    # -------------------------------------------------------------------------
    # In Web Simulator: click "+2 phút" button
    plus_2m_btn = sim_page.locator(".clock-buttons button").nth(1)
    plus_2m_btn.click()

    expect(oled_clock).to_contain_text("08:02:00", timeout=5000)

    # In Caregiver App: reload data and verify status transitioned to "Đã nhắc lại"
    app_page.get_by_role("button", name="Tải lại dữ liệu").click()
    time.sleep(1.5)
    expect(app_page.locator('[aria-label*="Thuốc A"][aria-label*="Đã nhắc lại"]').first).to_be_visible(timeout=8000)

    audit_tracker.record_screenshot(app_page, "18_cross_0802_reminder2.png", "Second reminder at 08:02:00 - Status Reminded (2 min)")

    # -------------------------------------------------------------------------
    # R4.4: Overdue Alert at 08:05:00 (+3m)
    # -------------------------------------------------------------------------
    # In Web Simulator: advance +3 minutes by clicking "+1 phút" 3 times deterministically
    for expected_time in ("08:03:00", "08:04:00", "08:05:00"):
        plus_1m_btn.click()
        expect(oled_clock).to_contain_text(expected_time, timeout=8000)

    # In Caregiver App: navigate to Alerts tab (x=294, y=820)
    app_page.mouse.click(294, 820)
    time.sleep(2.0)

    # Refresh alerts list in Alerts tab
    refresh_alerts_btn = app_page.get_by_role("button", name="Làm mới cảnh báo")
    if refresh_alerts_btn.is_visible():
        refresh_alerts_btn.click()
        time.sleep(1.5)

    # Verify Overdue alert card is present
    overdue_card = app_page.locator('[aria-label*="Chưa xác nhận Thuốc A ở ngăn 1"]').first
    expect(overdue_card).to_be_visible(timeout=8000)

    audit_tracker.record_screenshot(app_page, "19_cross_0805_alert_overdue.png", "Overdue alert at 08:05:00 - Overdue notification card displayed")

    # -------------------------------------------------------------------------
    # R4.5: Physical Dispense Resolution
    # -------------------------------------------------------------------------
    # In Web Simulator: Open Lid 1, Take pill (-0.5g), Close Lid 1, Press Confirm Button
    lid_btn = slot1_sim.locator("button.lid-button")
    dispense_btn = slot1_sim.locator("button.dispense-button")
    confirm_btn = slot1_sim.locator("button.confirm-button")

    # 1. Open Lid 1
    lid_btn.click()
    expect(slot1_sim.locator(".lid-badge")).to_contain_text("Nắp đang mở", timeout=5000)

    # 2. Dispense 1 pill (-0.5g)
    dispense_btn.click()
    expect(slot1_sim.locator(".pill-counter-tag strong")).to_have_text("9", timeout=5000)
    expect(slot1_sim.locator(".oled-value")).to_contain_text("4.5")

    # 3. Close Lid 1
    lid_btn.click()
    expect(slot1_sim.locator(".lid-badge")).to_contain_text("Nắp đã đóng", timeout=5000)

    # 4. Press Confirm button on casing
    confirm_btn.click()
    expect(slot1_sim.locator(".led-text")).to_have_text("LED TẮT", timeout=5000)
    expect(confirm_btn).not_to_be_visible()

    # In Caregiver App: Return to Today tab (x=42, y=820) and verify dose confirmed
    app_page.mouse.click(42, 820)
    time.sleep(1.0)
    app_page.get_by_role("button", name="Tải lại dữ liệu").click()
    time.sleep(2.0)

    # Verify status transitioned to "Đã xác nhận"
    expect(app_page.locator('[aria-label*="Thuốc A"][aria-label*="Đã xác nhận"]').first).to_be_visible(timeout=8000)

    audit_tracker.record_screenshot(app_page, "20_cross_resolved_dose.png", "Cross-UI resolution complete - Pill taken, hardware silenced, Caregiver App confirmed")

    # -------------------------------------------------------------------------
    # DevTools Quality Gate: Assert 0 uncaught errors on both pages
    # -------------------------------------------------------------------------
    audit_tracker.assert_no_uncaught_errors()
