# E2E Test Infra: Smart Pill Box Chrome DevTools Automation

## Test Philosophy
- **Zero-Mock Opaque-Box Automation**: Every test interacts with real compiled frontend code running on live HTTP ports communicating with a live FastAPI backend using a persistent SQLite database.
- **Real Browser Automation**: Driven via official Google Chrome (v155 64-bit) using Chrome DevTools Protocol (CDP) through Playwright.
- **Deep Observability**: Continuous DevTools console error logging (`page.on('console')`, `page.on('pageerror')`) to guarantee zero uncaught JavaScript exceptions across all user journeys.
- **Visual Evidence**: Screenshots captured at every milestone state into `reports/e2e_screenshots/`.

## Feature Inventory & Test Coverage
| # | Feature | Requirement | Tier 1 (Isolated) | Tier 2 (Boundary) | Tier 3 (Cross-Module) | Tier 4 (E2E Workflow) |
|---|---------|-------------|:-----------------:|:-----------------:|:---------------------:|:---------------------:|
| 1 | Backend & Seed | ORIGINAL_REQUEST §R1 | ✓ | ✓ | ✓ | ✓ |
| 2 | Web Simulator Host | ORIGINAL_REQUEST §R1 | ✓ | ✓ | ✓ | ✓ |
| 3 | Flutter Web Host | ORIGINAL_REQUEST §R1 | ✓ | ✓ | ✓ | ✓ |
| 4 | Operator Login | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 5 | 3D Lid Open/Close | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 6 | Load Cell & Noise | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 7 | Virtual Clock & OLED | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 8 | LED & Audio Buzzer | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 9 | Confirm Button | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 10 | Caregiver Login & Isolation | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 11 | Today Tab Live Feed | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 12 | Schedule & 409 Conflict | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 13 | Alerts & Quick Note Chips | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 14 | Medical Timeline View | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 15 | Cross-UI Real-time Flow | ORIGINAL_REQUEST §R4 | - | - | - | ✓ (07:59->08:05 E2E) |
| 16 | DevTools Console Audit | ORIGINAL_REQUEST §R5 | ✓ | ✓ | ✓ | ✓ (0 uncaught errors) |
| 17 | Milestone Screenshots | ORIGINAL_REQUEST §R5 | ✓ | ✓ | ✓ | ✓ (18+ captures) |

## Test Architecture
- **Runner**: Pytest 8.2 / Python 3.12 with standalone script `tests/e2e_chrome/run_all_e2e.py`.
- **Target URLs**:
  - Web Simulator: `http://localhost:5173`
  - Flutter Caregiver Web: `http://localhost:8080`
  - Backend API: `http://localhost:8000`
- **Output Directories**:
  - Test scripts: `tests/e2e_chrome/`
  - Screenshots: `reports/e2e_screenshots/`
  - Final Report: `E2E_CHROME_DEVTOOLS_REPORT.md`
