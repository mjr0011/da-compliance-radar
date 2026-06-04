"""
Test configuration.

Sets minimum env vars so `app.config` validates even when running
outside Docker. Override per-test via monkeypatch as needed.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-x")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("COMPANIES_HOUSE_API_KEY", "test-key")

import pytest  # noqa: E402


@pytest.fixture
def today_iso():
    from datetime import date
    return date.today().isoformat()
