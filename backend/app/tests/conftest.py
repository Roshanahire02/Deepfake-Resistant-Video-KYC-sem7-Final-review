"""Test-wide environment, applied before any app module is imported."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test.db")
os.environ["RATE_LIMIT_ENABLED"] = "false"  # individual tests re-enable it explicitly
