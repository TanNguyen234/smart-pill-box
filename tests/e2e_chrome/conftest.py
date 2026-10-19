"""Pytest configuration and fixtures for E2E Chrome DevTools Testing."""

import os
import sys
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

from typing import Generator, List, Dict, Any
import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, ConsoleMessage

from tests.e2e_chrome.service_manager import ServiceManager, SIMULATOR_URL, FLUTTER_URL, BACKEND_URL

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "e2e_screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ConsoleAuditTracker:
    """Collects and audits DevTools console messages and uncaught exceptions across all pages."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        self.page_errors: List[Dict[str, Any]] = []
        self.screenshots: List[Dict[str, str]] = []

    def attach_to_page(self, page: Page, name: str) -> None:
        def on_console(msg: ConsoleMessage):
            entry = {
                "page": name,
                "type": msg.type,
                "text": msg.text,
                "location": msg.location,
            }
            self.logs.append(entry)

        def on_pageerror(exc):
            err_entry = {
                "page": name,
                "error": str(exc),
            }
            self.page_errors.append(err_entry)

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

    def record_screenshot(self, page: Page, filename: str, description: str = "") -> str:
        """Captures a screenshot and registers it in the gallery."""
        target_path = SCREENSHOTS_DIR / filename
        page.screenshot(path=str(target_path), full_page=True)
        self.screenshots.append({
            "filename": filename,
            "path": str(target_path),
            "description": description,
        })
        try:
            print(f"[Screenshot] Captured {filename}: {description}")
        except Exception:
            clean_desc = description.encode("ascii", errors="replace").decode("ascii")
            print(f"[Screenshot] Captured {filename}: {clean_desc}")
        return str(target_path)

    def assert_no_uncaught_errors(self) -> None:
        """Asserts that 0 uncaught JavaScript errors or crashes occurred."""
        if self.page_errors:
            err_strs = [f"[{e['page']}] {e['error']}" for e in self.page_errors]
            pytest.fail(f"Detected {len(self.page_errors)} uncaught JS page error(s):\n" + "\n".join(err_strs))


@pytest.fixture(scope="session")
def live_services() -> Generator[ServiceManager, None, None]:
    """Session fixture that launches Backend, Simulator, and Flutter Web."""
    manager = ServiceManager()
    manager.start_all()
    try:
        yield manager
    finally:
        manager.stop_all()


@pytest.fixture(scope="session")
def audit_tracker() -> ConsoleAuditTracker:
    """Session fixture providing the global DevTools audit tracker."""
    return ConsoleAuditTracker()


@pytest.fixture(scope="session")
def chrome_browser() -> Generator[Browser, None, None]:
    """Launches Google Chrome binary using Playwright Chromium with DevTools enabled."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--force-renderer-accessibility",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
            ]
        )
        yield browser
        browser.close()


@pytest.fixture
def sim_context(chrome_browser: Browser) -> Generator[BrowserContext, None, None]:
    """Dedicated context for Web Simulator (Desktop Viewport 1280x800)."""
    context = chrome_browser.new_context(
        viewport={"width": 1280, "height": 800},
        base_url=SIMULATOR_URL,
    )
    yield context
    context.close()


@pytest.fixture
def app_context(chrome_browser: Browser) -> Generator[BrowserContext, None, None]:
    """Dedicated context for Flutter Caregiver Web (Mobile Viewport 420x860)."""
    context = chrome_browser.new_context(
        viewport={"width": 420, "height": 860},
        base_url=FLUTTER_URL,
    )
    yield context
    context.close()


@pytest.fixture
def sim_page(sim_context: BrowserContext, audit_tracker: ConsoleAuditTracker) -> Page:
    """Pre-configured page for Web Simulator with console listeners attached."""
    page = sim_context.new_page()
    audit_tracker.attach_to_page(page, "WebSimulator")
    return page


@pytest.fixture
def app_page(app_context: BrowserContext, audit_tracker: ConsoleAuditTracker) -> Page:
    """Pre-configured page for Flutter Web with console listeners attached."""
    page = app_context.new_page()
    audit_tracker.attach_to_page(page, "FlutterCaregiverApp")
    return page
