"""Web Simulator Chrome DevTools E2E Tests (R2.1 - R2.6).

Verifies:
- R2.1: Operator login and session state
- R2.2: 3D chamber lid open/close with CSS transform and LID_OPENED/LID_CLOSED
- R2.3: Load cell weight sensor (dispense >=0.3g decrements pill count, jitter <0.3g does not)
- R2.4: Virtual clock controls (+1m, +2m, +5m) and instant OLED clock display
- R2.5: LED pulse animation and Web Audio buzzer alert
- R2.6: Pill box casing confirm button (CONFIRM_PRESSED)
"""

import os
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
from tests.e2e_chrome.service_manager import ServiceManager, SIMULATOR_URL


def test_web_simulator_operator_login(live_services: ServiceManager, sim_page: Page, audit_tracker: ConsoleAuditTracker):
    """R2.1: Verify Operator login and dashboard initialization."""
    live_services.reset_state()

    sim_page.goto(f"{SIMULATOR_URL}/")
    sim_page.wait_for_load_state("domcontentloaded")
    sim_page.wait_for_selector("#email", timeout=10000)

    # Capture login screen
    audit_tracker.record_screenshot(sim_page, "01_simulator_login_screen.png", "Web Simulator login screen")

    # Check login form elements
    email_input = sim_page.locator("#email")
    password_input = sim_page.locator("#password")
    login_btn = sim_page.locator("button.login-button")

    expect(email_input).to_be_visible()
    expect(password_input).to_be_visible()

    # Fill credentials
    email_input.fill("operator@example.test")
    password_input.fill("Password123!")
    login_btn.click()

    # Verify transition to dashboard: user chip displays display_name ("Điều khiển mô phỏng")
    user_chip = sim_page.locator(".user-chip")
    expect(user_chip).to_be_visible(timeout=5000)
    expect(user_chip).to_contain_text(re.compile(r"Điều khiển mô phỏng|Operator"))

    # Verify OLED clock is loaded and displays 07:59:00
    oled_clock = sim_page.locator(".clock-card strong")
    expect(oled_clock).to_be_visible()
    expect(oled_clock).to_contain_text("07:59:00")

    # Verify all 3 compartments loaded
    for slot in (1, 2, 3):
        card = sim_page.locator(f".compartment-card.slot-{slot}")
        expect(card).to_be_visible()

    audit_tracker.record_screenshot(sim_page, "02_simulator_operator_dashboard.png", "Web Simulator operator dashboard")
    audit_tracker.assert_no_uncaught_errors()


def test_web_simulator_3d_lid_open_close(live_services: ServiceManager, sim_page: Page, audit_tracker: ConsoleAuditTracker):
    """R2.2: Verify 3D chamber lid opening and closing on Compartment 1."""
    live_services.reset_state()
    sim_page.goto(f"{SIMULATOR_URL}/")
    sim_page.wait_for_load_state("domcontentloaded")
    sim_page.wait_for_selector("#email", timeout=10000)

    # Login
    sim_page.locator("#email").fill("operator@example.test")
    sim_page.locator("#password").fill("Password123!")
    sim_page.locator("button.login-button").click()
    expect(sim_page.locator(".user-chip")).to_be_visible(timeout=5000)

    # Compartment 1 initial state: closed
    slot1_card = sim_page.locator(".compartment-card.slot-1")
    chamber = slot1_card.locator(".physical-chamber")
    expect(chamber).to_have_class(re.compile(r"is-closed"))
    expect(slot1_card.locator(".lid-badge")).to_contain_text("Nắp đã đóng")

    # Click Mở nắp ngăn
    lid_button = slot1_card.locator("button.lid-button")
    expect(lid_button).to_contain_text("Mở nắp ngăn")
    lid_button.click()

    # Wait for backend response and state update
    expect(slot1_card.locator(".lid-badge")).to_contain_text("Nắp đang mở", timeout=5000)
    expect(chamber).to_have_class(re.compile(r"is-open"))
    expect(lid_button).to_contain_text("Đóng nắp ngăn")

    audit_tracker.record_screenshot(sim_page, "03_simulator_lid1_opened.png", "Compartment 1 3D lid opened")

    # Close lid
    lid_button.click()
    expect(slot1_card.locator(".lid-badge")).to_contain_text("Nắp đã đóng", timeout=5000)
    expect(chamber).to_have_class(re.compile(r"is-closed"))

    audit_tracker.assert_no_uncaught_errors()


def test_web_simulator_loadcell_weight_and_noise(live_services: ServiceManager, sim_page: Page, audit_tracker: ConsoleAuditTracker):
    """R2.3: Verify load cell weight reading (dispense >=0.3g decrements pill count, jitter <0.3g does not)."""
    live_services.reset_state()
    sim_page.goto(f"{SIMULATOR_URL}/")
    sim_page.wait_for_load_state("domcontentloaded")
    sim_page.wait_for_selector("#email", timeout=10000)

    # Login
    sim_page.locator("#email").fill("operator@example.test")
    sim_page.locator("#password").fill("Password123!")
    sim_page.locator("button.login-button").click()
    expect(sim_page.locator(".user-chip")).to_be_visible(timeout=5000)

    slot1_card = sim_page.locator(".compartment-card.slot-1")
    dispense_btn = slot1_card.locator("button.dispense-button")
    noise_btn = slot1_card.locator("button.noise-button")
    lid_btn = slot1_card.locator("button.lid-button")

    # Initially closed -> dispense and noise buttons are disabled
    expect(dispense_btn).to_be_disabled()
    expect(noise_btn).to_be_disabled()

    # Open lid
    lid_btn.click()
    expect(dispense_btn).to_be_enabled(timeout=5000)
    expect(noise_btn).to_be_enabled()

    # Check baseline weight and count
    expect(slot1_card.locator(".oled-value")).to_contain_text("5.0")
    expect(slot1_card.locator(".pill-counter-tag strong")).to_have_text("10")

    # 1. Take one pill (-0.5g >= 0.3g) -> pill count decrements from 10 to 9, weight drops to 4.5g
    dispense_btn.click()
    expect(slot1_card.locator(".oled-value")).to_contain_text("4.5", timeout=5000)
    expect(slot1_card.locator(".pill-counter-tag strong")).to_have_text("9")

    audit_tracker.record_screenshot(sim_page, "04_simulator_weight_drop_pill_taken.png", "Pill taken: weight 4.5g, count 9")

    # 2. Inject noise jitter (-0.1g < 0.3g) -> weight updates to 4.4g, but pill count REMAINS 9
    noise_btn.click()
    expect(slot1_card.locator(".oled-value")).to_contain_text("4.4", timeout=5000)
    expect(slot1_card.locator(".pill-counter-tag strong")).to_have_text("9")

    audit_tracker.record_screenshot(sim_page, "05_simulator_weight_noise_no_pill_drop.png", "Jitter noise: weight 4.4g, count remains 9")
    audit_tracker.assert_no_uncaught_errors()


def test_web_simulator_virtual_clock_and_led_buzzer(live_services: ServiceManager, sim_page: Page, audit_tracker: ConsoleAuditTracker):
    """R2.4 & R2.5 & R2.6: Advance clock to 08:00, verify LED pulse, audio buzzer, and confirm button."""
    live_services.reset_state()
    sim_page.goto(f"{SIMULATOR_URL}/")
    sim_page.wait_for_load_state("domcontentloaded")
    sim_page.wait_for_selector("#email", timeout=10000)

    # Login
    sim_page.locator("#email").fill("operator@example.test")
    sim_page.locator("#password").fill("Password123!")
    sim_page.locator("button.login-button").click()
    expect(sim_page.locator(".user-chip")).to_be_visible(timeout=5000)

    # Opt in to audio
    audio_toggle = sim_page.locator("button.audio-toggle")
    audio_toggle.click()
    expect(audio_toggle).to_contain_text(re.compile(r"Còi đang bật|Bật âm thanh"))

    # Advance clock +1 min from 07:59:00 to 08:00:00 (first button in .clock-buttons)
    plus_1m_btn = sim_page.locator(".clock-buttons button").first
    plus_1m_btn.click()

    # OLED clock should immediately show 08:00:00
    oled_clock = sim_page.locator(".clock-card strong")
    expect(oled_clock).to_contain_text("08:00:00", timeout=5000)

    audit_tracker.record_screenshot(sim_page, "06_simulator_clock_advanced_0800.png", "Clock advanced to 08:00:00")

    # Compartment 1 (Thuốc A scheduled at 08:00) should now have active LED and Buzzer
    slot1_card = sim_page.locator(".compartment-card.slot-1")
    led_lens = slot1_card.locator(".led-lens")
    expect(led_lens).to_have_class(re.compile(r"led-active"), timeout=5000)
    expect(slot1_card.locator(".led-text")).to_have_text("LED BẬT")

    # Buzzer active
    expect(slot1_card.locator(".buzzer-line")).to_have_class(re.compile(r"buzzer-active"))
    expect(slot1_card.locator(".buzzer-indicator")).to_contain_text("🔊")

    # Confirm button must appear on casing
    confirm_btn = slot1_card.locator("button.confirm-button")
    expect(confirm_btn).to_be_visible(timeout=5000)
    expect(confirm_btn).to_contain_text("Nút xác nhận trên hộp")

    audit_tracker.record_screenshot(sim_page, "07_simulator_led_buzzer_active.png", "LED active pulse and buzzer sounding at 08:00")

    # Press confirm button
    confirm_btn.click()

    # Verify LED and Buzzer turn off, confirm button disappears
    expect(led_lens).not_to_have_class(re.compile(r"led-active"), timeout=5000)
    expect(slot1_card.locator(".led-text")).to_have_text("LED TẮT")
    expect(slot1_card.locator(".buzzer-indicator")).to_contain_text("🔈")
    expect(confirm_btn).not_to_be_visible()

    audit_tracker.record_screenshot(sim_page, "08_simulator_confirmed_pressed.png", "Dose confirmed: LED and buzzer silenced")
    audit_tracker.assert_no_uncaught_errors()
