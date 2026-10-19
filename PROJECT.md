# Project: Smart Pill Box E2E Chrome DevTools Testing

## Architecture
The Smart Pill Box system consists of three live cooperating tiers running locally without any mocks:
1. **Backend FastAPI (:8000)**: Core business rules, hardware event processing, virtual clock state machine, and SQLite persistent storage (`backend/data/smartpill.sqlite3`).
2. **Web Simulator (:5173)**: React 19 + Vite web interface serving as the physical IoT hardware surrogate (3D chambers, load cell sensors, OLED clock display, LED indicators, Web Audio buzzer, confirm buttons).
3. **Caregiver App (:8080)**: Flutter Web application providing caregiver views (Today schedule, 24h schedule manager, overdue alert resolution with Quick Note Chips, medical timeline history).
4. **E2E Automation Harness (Playwright + Chrome DevTools)**: Python 3.12 + Playwright 1.61 controlling the system Google Chrome binary (`C:\Program Files\Google\Chrome\Application\chrome.exe`) over Chrome DevTools Protocol (CDP), intercepting DevTools console logs, capturing high-resolution milestone screenshots, and synchronizing cross-UI state.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1.1 Backend Service & Seed | Run live FastAPI on :8000 with sqlite seed `scripts/seed_demo.py` and verify `/api/simulation/state` | M1 | ORIGINAL_REQUEST §R1 |
| 2 | R1.2 Web Simulator Hosting | Serve React/Vite simulator on :5173 connecting to live backend | M1 | ORIGINAL_REQUEST §R1 |
| 3 | R1.3 Flutter Web Hosting | Serve Flutter Web Caregiver App on :8080 connecting to live backend | M1 | ORIGINAL_REQUEST §R1 |
| 4 | R1.4 Test Infrastructure Harness | Zero-mock service manager, Chrome CDP launcher, console log interceptor, screenshot manager | M1 | ORIGINAL_REQUEST §R1, §R5 |
| 5 | R2.1 Operator Login | Authenticate `operator@example.test` in Web Simulator and store token | M2 | ORIGINAL_REQUEST §R2 |
| 6 | R2.2 3D Lid Open/Close | Open/close 3D lids for compartments 1..3, verify CSS rotateX and backend `LID_OPENED` event | M2 | ORIGINAL_REQUEST §R2 |
| 7 | R2.3 Load Cell Weight & Noise | Dispense pill (drop >=0.3g decrements count) vs jitter noise (drop 0.1g <0.3g preserves count) | M2 | ORIGINAL_REQUEST §R2 |
| 8 | R2.4 Virtual Clock Controls | Advance time (+1m, +2m, +5m), verify instant OLED clock update | M2 | ORIGINAL_REQUEST §R2 |
| 9 | R2.5 LED & Buzzer Indicator | Verify LED pulse animation (`.led-active`) and audio buzzer trigger on dose time | M2 | ORIGINAL_REQUEST §R2 |
| 10 | R2.6 Confirm Button | Verify confirm button on pill box casing sends `CONFIRM_PRESSED` | M2 | ORIGINAL_REQUEST §R2 |
| 11 | R3.1 Caregiver A Login & Isolation | Authenticate `caregiver-a@example.test`, verify patient data isolation from Caregiver B | M3 | ORIGINAL_REQUEST §R3 |
| 12 | R3.2 Today Tab Verification | Verify SIM-001 connection status, daily dose cards, next scheduled dose | M3 | ORIGINAL_REQUEST §R3 |
| 13 | R3.3 Schedule Tab & 409 Conflict | Add 24h schedule (`HH:mm`), verify duplicate schedule returns HTTP 409 and displays error | M3 | ORIGINAL_REQUEST §R3 |
| 14 | R3.4 Alerts Tab & Quick Note Chips | Open overdue alert resolution modal, select Quick Note Chip, verify transition to `CHECKED` | M3 | ORIGINAL_REQUEST §R3 |
| 15 | R3.5 Medical Timeline View | Verify History tab updates with hardware events (lid open, weight change, dose confirm) | M3 | ORIGINAL_REQUEST §R3 |
| 16 | R4.1 Timeline 07:59 Idle State | Initial synchronized state, lids closed, dose pending soon | M4 | ORIGINAL_REQUEST §R4 |
| 17 | R4.2 Timeline 08:00 Pending State | Clock +1m -> Simulator activates LED & buzzer; Flutter Today tab shows dose pending | M4 | ORIGINAL_REQUEST §R4 |
| 18 | R4.3 Timeline 08:02 Reminded State | Clock +2m -> System sends reminder 2, UI updates reminder status | M4 | ORIGINAL_REQUEST §R4 |
| 19 | R4.4 Timeline 08:05 Overdue State | Clock +3m -> Dose overdue, Flutter Alerts tab displays red overdue card | M4 | ORIGINAL_REQUEST §R4 |
| 20 | R4.5 Timeline Pill Taken & Resolve | Lid 1 open -> drop 0.5g -> confirm button -> dose resolved, LED/buzzer off, alert resolved | M4 | ORIGINAL_REQUEST §R4 |
| 21 | R5.1 Automated Test Suite | Standalone executable test suite in `tests/e2e_chrome/` with Pytest runner | M5 | ORIGINAL_REQUEST §R5 |
| 22 | R5.2 Visual Screenshots | Milestone screenshots captured at all critical states in `reports/e2e_screenshots/` | M5 | ORIGINAL_REQUEST §R5 |
| 23 | R5.3 Console Logs Audit | Continuous Chrome DevTools console interception verifying 0 uncaught JS errors | M5 | ORIGINAL_REQUEST §R5 |
| 24 | R5.4 Comprehensive Delivery Report | Formatted markdown delivery report `E2E_CHROME_DEVTOOLS_REPORT.md` with full evidence | M5 | ORIGINAL_REQUEST §R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | E2E Service Infrastructure & Harness | Service manager (:8000, :5173, :8080), conftest fixtures, CDP Chrome launcher, console listener | none | PLANNED |
| M2 | Web Simulator Chrome Automation Suite | Test script for R2.1 - R2.6 in real Chrome DevTools | M1 | PLANNED |
| M3 | Flutter Web Caregiver App Automation Suite | Test script for R3.1 - R3.5 in real Chrome DevTools | M1 | PLANNED |
| M4 | Cross-UI Real-time Medical Timeline Scenario | Synchronized dual-browser test for R4.1 - R4.5 | M2, M3 | PLANNED |
| M5 | E2E Runner, Screenshots, Audit & Final Report | Execution of full suite, console audit, screenshots check, E2E_CHROME_DEVTOOLS_REPORT.md | M4 | PLANNED |

## Interface Contracts
### Service Manager ↔ Test Suites
- `ServiceManager.start_all()`: Launches FastAPI on 8000, Vite preview/http on 5173, and Flutter Web on 8080.
- `ServiceManager.wait_ready()`: Polls `http://127.0.0.1:8000/api/simulation/state`, `http://127.0.0.1:5173`, `http://127.0.0.1:8080`.
- `ServiceManager.reset_state()`: Calls `POST http://127.0.0.1:8000/api/simulation/reset` to re-seed and reset clock to 07:59:00.
- `ServiceManager.stop_all()`: Cleanly terminates background processes on teardown.

### Chrome DevTools Automation ↔ Application UIs
- Playwright Chromium instance launched with `channel="chrome"`, `args=["--force-renderer-accessibility"]`.
- `page.on("console", ...)` and `page.on("pageerror", ...)` track all console messages and assert 0 uncaught exceptions.
- Web Simulator Target: `http://localhost:5173` (Desktop viewport 1280x800).
- Flutter Web Target: `http://localhost:8080` (Mobile viewport 420x860, CanvasKit accessibility enabled via evaluate click on `flt-semantics-placeholder`).

## Code Layout
- `tests/e2e_chrome/`:
  - `service_manager.py`: Coordinates live processes on :8000, :5173, :8080.
  - `conftest.py`: Pytest fixtures for browser contexts, pages, console listeners, screenshot helpers.
  - `test_web_simulator.py`: Web Simulator test suite (R2).
  - `test_caregiver_app.py`: Flutter Web Caregiver App test suite (R3).
  - `test_cross_ui_timeline.py`: Synchronized cross-UI medical timeline scenario (R4).
  - `run_all_e2e.py`: Standalone master runner executing all suites, verifying console logs, capturing screenshots, and compiling metrics.
- `reports/e2e_screenshots/`:
  - 18+ milestone screenshots named systematically (e.g. `01_simulator_login.png`, `02_lid_opened.png`, etc.).
- `E2E_CHROME_DEVTOOLS_REPORT.md`: Comprehensive delivery report at project root.
