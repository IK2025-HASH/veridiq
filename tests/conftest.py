# Copyright © 2026 Network Logic Limited. All rights reserved.
# Shared pytest fixtures + hermetic test environment.
#
# IMPORTANT: this file is imported by pytest BEFORE any test module, so the
# environment variables below are set before `app` is first imported. That pins
# the whole suite to a throwaway SQLite database — no Postgres, no network, no
# real Anthropic key. Do not import `app.*` at the top of this file.

import os
import tempfile

# --- Hermetic environment (must be set before app import) ---
_TEST_DB = tempfile.mktemp(prefix="veridiq_test_", suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-placeholder"
os.environ["ENVIRONMENT"] = "development"

import pytest
from fastapi.testclient import TestClient

# Admin credentials used to drive the first-boot setup wizard in tests.
ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "password1234"


@pytest.fixture(scope="session")
def client():
    """A TestClient that runs the app lifespan (create_tables, settings load).

    Used as a context manager so startup/shutdown events actually fire.
    """
    from app.main import app
    with TestClient(app, follow_redirects=False) as c:
        yield c


@pytest.fixture(scope="session")
def admin_client(client):
    """The same client, with first-boot setup completed and admin logged in.

    Setup runs once per session. The fake `sk-ant-` key is accepted by the
    wizard (it is not validated against the API at setup time).
    """
    r = client.post(
        "/setup",
        data={
            "admin_email": ADMIN_EMAIL,
            "admin_password": ADMIN_PASSWORD,
            "anthropic_api_key": "sk-ant-test-placeholder",
        },
    )
    # Wizard redirects to /admin on success (302). If setup was already done in a
    # prior fixture call it redirects to / (302). Either way: a redirect, not 5xx.
    assert r.status_code in (302, 303), f"setup failed: {r.status_code} {r.text[:300]}"
    return client
