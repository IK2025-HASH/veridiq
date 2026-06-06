# Copyright © 2026 Network Logic Limited. All rights reserved.
# Playwright screenshot + smoke tests for key public and auth pages.
# Run separately from the unit suite:
#   playwright install chromium
#   pytest tests/test_playwright.py --browser chromium -v
#
# A live uvicorn process is started once per session against a throw-away
# SQLite database. Screenshots land in screenshots/ for artifact upload.

import os
import subprocess
import sys
import time

import pytest
from playwright.sync_api import Page, expect

SCREENSHOTS = "screenshots"
_SERVER_PORT = 8899
_BASE = f"http://127.0.0.1:{_SERVER_PORT}"


@pytest.fixture(scope="session")
def live_server():
    os.makedirs(SCREENSHOTS, exist_ok=True)
    db_path = os.path.abspath("test_playwright.db")
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
        "SECRET_KEY": "playwright-test-secret-not-for-prod",
        "ANTHROPIC_API_KEY": "sk-ant-test-placeholder",
        "ENVIRONMENT": "development",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(_SERVER_PORT)],
        env=env,
    )
    time.sleep(3)
    yield _BASE
    proc.terminate()
    proc.wait()
    for path in (db_path,):
        if os.path.exists(path):
            os.remove(path)


def test_landing_page(page: Page, live_server):
    page.goto(f"{live_server}/landing")
    expect(page.locator("body")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/01-landing.png", full_page=True)


def test_login_page(page: Page, live_server):
    page.goto(f"{live_server}/login")
    expect(page.locator("input[name=email]")).to_be_visible()
    expect(page.locator("input[name=password]")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/02-login.png", full_page=True)


def test_register_page(page: Page, live_server):
    page.goto(f"{live_server}/register")
    expect(page.locator("body")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/03-register.png", full_page=True)


def test_homepage_desktop(page: Page, live_server):
    page.goto(f"{live_server}/")
    expect(page.locator("body")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/04-homepage-desktop.png", full_page=True)


def test_homepage_mobile(page: Page, live_server):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{live_server}/")
    # Hamburger visible on mobile
    expect(page.locator("#nav-hamburger")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/05-homepage-mobile.png", full_page=True)


def test_hamburger_opens_menu(page: Page, live_server):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{live_server}/")
    page.click("#nav-hamburger")
    expect(page.locator("#mobile-menu")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/06-mobile-menu-open.png", full_page=True)


def test_terms_page(page: Page, live_server):
    page.goto(f"{live_server}/terms")
    expect(page.locator("body")).to_be_visible()
    page.screenshot(path=f"{SCREENSHOTS}/07-terms.png", full_page=True)
