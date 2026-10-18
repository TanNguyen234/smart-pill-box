"""Test configuration: production credentials are never committed."""
import os
os.environ.setdefault("JWT_SECRET", "only-for-pytest-not-production")
