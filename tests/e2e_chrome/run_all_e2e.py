"""Master E2E Chrome DevTools Test Runner for Smart Pill Box.

Orchestrates full-system automated verification across:
- Web Simulator (Desktop Viewport 1280x800 on http://127.0.0.1:5173)
- Flutter Web Caregiver App (Mobile Viewport 420x860 on http://127.0.0.1:8080)
- FastAPI Backend (http://127.0.0.1:8000)

Validates:
1. 100% test pass rate across all suites:
   - tests/e2e_chrome/test_web_simulator.py (R2.1 - R2.6)
   - tests/e2e_chrome/test_caregiver_app.py (R3.1 - R3.5)
   - tests/e2e_chrome/test_cross_ui_timeline.py (R4.1 - R4.5)
2. Zero uncaught JavaScript errors or unhandled exceptions across all DevTools sessions.
3. Completeness of all 20 milestone screenshots in reports/e2e_screenshots/.
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCREENSHOTS_DIR = PROJECT_ROOT / "reports" / "e2e_screenshots"
REPORTS_DIR = PROJECT_ROOT / "reports"

EXPECTED_SCREENSHOTS = [
    ("01_simulator_login_screen.png", "Web Simulator login screen with operator credentials"),
    ("02_simulator_operator_dashboard.png", "Web Simulator operator dashboard with OLED clock & 3 chambers"),
    ("03_simulator_lid1_opened.png", "Compartment 1 3D lid opened with CSS rotateX transform"),
    ("04_simulator_weight_drop_pill_taken.png", "Pill taken: weight drops 0.5g (>=0.3g threshold), pill count decrements"),
    ("05_simulator_weight_noise_no_pill_drop.png", "Load cell noise jitter (-0.1g < 0.3g), pill count remains unchanged"),
    ("06_simulator_clock_advanced_0800.png", "Virtual clock advanced to 08:00:00, instant OLED display sync"),
    ("07_simulator_led_buzzer_active.png", "Scheduled dose reminder: LED lens active pulse & buzzer sounding"),
    ("08_simulator_confirmed_pressed.png", "Hardware confirm button pressed: LED & buzzer silenced"),
    ("09_caregiver_login_screen.png", "Caregiver Mobile App login screen"),
    ("10_caregiver_today_dashboard.png", "Caregiver dashboard with Patient A and isolation from Patient B"),
    ("11_caregiver_today_dose_cards.png", "Today tab daily dose cards for slots 1, 2, 3"),
    ("12_caregiver_schedule_conflict_error.png", "Schedule 409 Conflict error for duplicate time/slot"),
    ("13_caregiver_alert_modal_quick_chips.png", "Alert resolution modal with Quick Note Chips"),
    ("14_caregiver_alert_resolved_checked.png", "Alert transitioned to CHECKED with Quick Note note"),
    ("15_caregiver_medical_timeline_view.png", "Caregiver Medical Timeline View with hardware events"),
    ("16_cross_0759_standby.png", "Standby baseline at 07:59:00 - Slot 1 standby"),
    ("17_cross_0800_alarm_led_buzzer.png", "Alarm triggered at 08:00:00 - LED pulse and Buzzer active"),
    ("18_cross_0802_reminder2.png", "Second reminder at 08:02:00 - Status Reminded (2 min)"),
    ("19_cross_0805_alert_overdue.png", "Overdue alert at 08:05:00 - Overdue notification card displayed"),
    ("20_cross_resolved_dose.png", "Cross-UI resolution complete - Pill taken, hardware silenced, Caregiver App confirmed"),
]


def run_test_suite() -> int:
    """Executes pytest across all e2e test modules."""
    print("=" * 80)
    print(" SMART PILL BOX - END-TO-END CHROME DEVTOOLS AUTOMATION TEST SUITE")
    print("=" * 80)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Screenshots Directory: {SCREENSHOTS_DIR}")
    print(f"Python Executable: {sys.executable}")
    print("-" * 80)

    test_targets = [
        "tests/e2e_chrome/test_web_simulator.py",
        "tests/e2e_chrome/test_caregiver_app.py",
        "tests/e2e_chrome/test_cross_ui_timeline.py",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *test_targets,
        "-v",
        "-s",
        "--tb=short",
    ]

    start_time = time.time()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    duration = time.time() - start_time

    print("\n" + "=" * 80)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Duration: {duration:.2f} seconds")
    print(f"Exit Code: {result.returncode}")

    # Audit screenshots
    print("\n" + "-" * 80)
    print(" MILESTONE SCREENSHOT AUDIT (20 Artifacts)")
    print("-" * 80)
    missing = []
    found = 0
    total_bytes = 0

    for filename, desc in EXPECTED_SCREENSHOTS:
        file_path = SCREENSHOTS_DIR / filename
        if file_path.exists() and file_path.stat().st_size > 0:
            size_kb = file_path.stat().st_size / 1024
            total_bytes += file_path.stat().st_size
            print(f"  [OK] {filename:<40} ({size_kb:6.1f} KB) - {desc}")
            found += 1
        else:
            print(f"  [MISSING] {filename:<36} - {desc}")
            missing.append(filename)

    print("-" * 80)
    print(f"Screenshot Status: {found}/{len(EXPECTED_SCREENSHOTS)} captured ({total_bytes / 1024:.1f} KB total)")

    if result.returncode == 0 and len(missing) == 0:
        print("\n[SUCCESS] ALL ZERO-MOCK E2E TESTS PASSED WITH ZERO INTEGRITY VIOLATIONS!")
        return 0
    else:
        print(f"\n[FAILURE] Tests failed or missing screenshots ({len(missing)} missing).")
        return 1


if __name__ == "__main__":
    sys.exit(run_test_suite())
