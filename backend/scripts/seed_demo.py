import os
from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")

from app.main import app
from app.seed import seed_demo


password = os.getenv("DEMO_PASSWORD")
if not password:
    raise SystemExit("Thiếu DEMO_PASSWORD trong backend/.env.")
seed_demo(app.state.session_factory, password)
print("Demo seed completed.")
