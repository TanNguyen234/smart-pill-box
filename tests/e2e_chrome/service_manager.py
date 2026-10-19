"""Service Manager for Zero-Mock E2E Chrome Testing.

Orchestrates live local instances of:
- Backend: FastAPI on 127.0.0.1:8000 (SQLite backed, seeded with seed_demo.py)
- Web Simulator: Static server on 127.0.0.1:5173 (serving web-simulator/dist)
- Flutter Caregiver App: Static server on 127.0.0.1:8080 (serving flutter-app/build/web)
"""

import os
import sys
import time
import uuid
import socket
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
BACKEND_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
WEB_SIMULATOR_DIR = PROJECT_ROOT / "web-simulator" / "dist"
FLUTTER_WEB_DIR = PROJECT_ROOT / "flutter-app" / "build" / "web"

BACKEND_URL = "http://127.0.0.1:8000"
SIMULATOR_URL = "http://127.0.0.1:5173"
FLUTTER_URL = "http://127.0.0.1:8080"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is currently occupied."""
    for check_host in ("127.0.0.1", "0.0.0.0"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((check_host, port))
        except OSError:
            return True
    return False


def kill_process_on_port(port: int) -> None:
    """Kill any process holding a specific port on Windows."""
    try:
        cmd = (
            f'powershell -NoProfile -Command "'
            f'Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | '
            f'Where-Object {{ $_.OwningProcess -gt 4 }} | '
            f'ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"'
        )
        subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        time.sleep(0.5)
    except Exception:
        pass


def kill_proc_tree(pid: int) -> None:
    """Force kill a process and all its children on Windows."""
    try:
        subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True, timeout=5)
    except Exception:
        pass


class ServiceManager:
    """Supervises the lifecycle of Backend, Web Simulator, and Flutter Web."""

    def __init__(self):
        self.backend_proc: Optional[subprocess.Popen] = None
        self.simulator_proc: Optional[subprocess.Popen] = None
        self.flutter_proc: Optional[subprocess.Popen] = None
        self.python_exe = sys.executable
        self.backend_python = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else sys.executable
        self._operator_token: Optional[str] = None

    def seed_database(self) -> None:
        """Runs the demo seed script against backend SQLite."""
        seed_script = BACKEND_DIR / "scripts" / "seed_demo.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BACKEND_DIR)
        res = subprocess.run(
            [self.backend_python, str(seed_script)],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[ServiceManager] Seed completed: {res.stdout.strip()}")

    def start_all(self) -> None:
        """Starts all 3 services and waits until they are healthy."""
        # 1. Clean existing ports if occupied
        for port in (8000, 5173, 8080):
            if is_port_in_use(port):
                print(f"[ServiceManager] Port {port} in use, terminating existing process...")
                kill_process_on_port(port)
                deadline = time.time() + 5.0
                while time.time() < deadline and is_port_in_use(port):
                    time.sleep(0.2)

        time.sleep(1.0)

        # 2. Seed database
        self.seed_database()

        # 3. Start Backend FastAPI on 0.0.0.0:8000
        print("[ServiceManager] Launching FastAPI backend on 0.0.0.0:8000...")
        backend_env = os.environ.copy()
        backend_env["PYTHONPATH"] = str(BACKEND_DIR)
        backend_log_path = PROJECT_ROOT / "reports" / "backend_server.log"
        self._backend_log = open(backend_log_path, "w", encoding="utf-8")
        self.backend_proc = subprocess.Popen(
            [self.backend_python, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
            cwd=str(BACKEND_DIR),
            env=backend_env,
            stdout=self._backend_log,
            stderr=self._backend_log,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        # 4. Start Web Simulator Static Server on :5173 on 0.0.0.0
        print(f"[ServiceManager] Launching Web Simulator on 0.0.0.0:5173 from {WEB_SIMULATOR_DIR}...")
        self.simulator_proc = subprocess.Popen(
            [self.python_exe, "-m", "http.server", "5173", "--directory", str(WEB_SIMULATOR_DIR), "--bind", "0.0.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        # 5. Start Flutter Web Static Server on :8080 on 0.0.0.0
        print(f"[ServiceManager] Launching Flutter Web on 0.0.0.0:8080 from {FLUTTER_WEB_DIR}...")
        self.flutter_proc = subprocess.Popen(
            [self.python_exe, "-m", "http.server", "8080", "--directory", str(FLUTTER_WEB_DIR), "--bind", "0.0.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        # 6. Wait for all 3 services to respond with HTTP 200
        self.wait_for_services()

        # 7. Pre-cache operator token to avoid redundant Argon2 hashing during resets
        self.get_operator_token()

    def _check_http(self, url: str) -> bool:
        """Performs a quick HTTP GET to see if service responds."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ServiceManager/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 204)
        except urllib.error.HTTPError as e:
            return e.code in (200, 204, 401, 403)
        except Exception:
            return False

    def wait_for_services(self, timeout_seconds: float = 30.0) -> None:
        """Polls health check URLs on all 3 services."""
        deadline = time.time() + timeout_seconds
        services = {
            "Backend (:8000)": f"{BACKEND_URL}/api/health",
            "Web Simulator (:5173)": f"{SIMULATOR_URL}/",
            "Flutter Web (:8080)": f"{FLUTTER_URL}/",
        }

        ready = {name: False for name in services}
        print("[ServiceManager] Polling services for readiness...")

        while time.time() < deadline:
            for name, url in services.items():
                if not ready[name] and self._check_http(url):
                    ready[name] = True
                    print(f"  [OK] {name} is READY at {url}")

            if all(ready.values()):
                print("[ServiceManager] All services verified healthy and ready!")
                return
            time.sleep(0.5)

        unready = [name for name, is_ready in ready.items() if not is_ready]
        raise TimeoutError(f"Services failed to become ready within {timeout_seconds}s: {unready}")

    def get_operator_token(self) -> str:
        """Obtains and caches an operator JWT token with 15s timeout."""
        if self._operator_token:
            return self._operator_token

        login_url = f"{BACKEND_URL}/api/auth/login"
        payload = json.dumps({"email": "operator@example.test", "password": "Password123!"}).encode("utf-8")
        req = urllib.request.Request(
            login_url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self._operator_token = data["access_token"]
            return self._operator_token

    def reset_state(self) -> Dict[str, Any]:
        """Resets the simulation state and clock back to 07:59:00 via API."""
        token = self.get_operator_token()

        reset_url = f"{BACKEND_URL}/api/simulation/reset"
        reset_payload = json.dumps({
            "confirm": True,
            "event_uuid": str(uuid.uuid4())
        }).encode("utf-8")
        reset_req = urllib.request.Request(
            reset_url,
            data=reset_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        try:
            with urllib.request.urlopen(reset_req, timeout=15) as resp:
                state = json.loads(resp.read().decode("utf-8"))
                print(f"[ServiceManager] Simulation state reset to {state.get('virtual_clock')}")
                return state
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token might have expired, invalidate and retry once
                self._operator_token = None
                token = self.get_operator_token()
                retry_req = urllib.request.Request(
                    reset_url,
                    data=reset_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                )
                with urllib.request.urlopen(retry_req, timeout=15) as resp:
                    state = json.loads(resp.read().decode("utf-8"))
                    print(f"[ServiceManager] Simulation state reset to {state.get('virtual_clock')} (after re-auth)")
                    return state
            raise

    def stop_all(self) -> None:
        """Cleanly shuts down all managed processes."""
        print("[ServiceManager] Terminating all services...")
        self._operator_token = None
        for proc, name in [
            (self.backend_proc, "Backend"),
            (self.simulator_proc, "Web Simulator"),
            (self.flutter_proc, "Flutter Web")
        ]:
            if proc is not None:
                try:
                    kill_proc_tree(proc.pid)
                    print(f"  [OK] {name} (PID {proc.pid}) terminated.")
                except Exception as e:
                    print(f"  [FAIL] Failed to terminate {name}: {e}")

        if hasattr(self, "_backend_log") and self._backend_log and not self._backend_log.closed:
            try:
                self._backend_log.close()
            except Exception:
                pass

        self.backend_proc = None
        self.simulator_proc = None
        self.flutter_proc = None

        # Double check ports
        for port in (8000, 5173, 8080):
            kill_process_on_port(port)
        print("[ServiceManager] Teardown complete.")


if __name__ == "__main__":
    manager = ServiceManager()
    try:
        manager.start_all()
        print("Testing reset_state()...")
        state = manager.reset_state()
        print("Current clock:", state.get("virtual_clock"))
        print("Compartments:", len(state.get("compartments", [])))
        print("SUCCESS! Press Ctrl+C or wait 3s to stop...")
        time.sleep(3)
    finally:
        manager.stop_all()
