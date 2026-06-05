# Copyright © 2026 Network Logic Limited. All rights reserved.
#
# STEP-0 SMOKE TEST — the safety net for the EVOLVE-NEVER-BREAK directive.
#
# Purpose: prove the app boots and the core user journey + platform pages render
# without server errors, and that key structural invariants hold. Run this green
# before AND after every incremental refactor step; if it goes red, the step
# broke something — roll back to the step's freeze.
#
#   pytest tests/test_smoke.py -q

import pathlib
import pytest

# ── Pages that MUST render 200 for a logged-in admin (the core journey) ──────────
CORE_PAGES_200 = [
    "/landing",
    "/terms",
    "/privacy",
    "/dashboard",
    "/projects",                      # project browser (Tier 1)
    "/projects/APR/stories",          # backlog (Tier 1)
    "/generate/APR-28",               # per-issue generate (Tier 2)
    "/credits",
    "/profile",
    "/team",
    "/invoices",
    "/security",
    "/admin",                         # admin console
    "/admin/settings",
    "/admin/users",
]

# ── JSON APIs that MUST return 200 ───────────────────────────────────────────────
CORE_APIS_200 = [
    "/api/health",
    "/api/generation-types",
    "/api/jira/status",
    "/api/credits/balance",
]

# ── GET routes that must not 5xx, but a controlled 4xx is expected/acceptable ────
# (Jira is not connected in tests, so these return 400 — never 500.)
SOFT_GET_ROUTES = [
    "/api/jira/projects",
    "/api/jira/projects/APR/issues",
    "/api/jira/issue/APR-28",
    "/login",
    "/register",
    "/auth/forgot-password",
    "/auth/verify-email-sent",
    "/setup",                         # redirects (302) once setup is complete
    "/",                              # redirects (302) to /dashboard when logged in
]


def test_app_boots(admin_client):
    """Lifespan ran and the health endpoint answers — the app is alive."""
    r = admin_client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("path", CORE_PAGES_200)
def test_core_pages_render(admin_client, path):
    r = admin_client.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}\n{r.text[:300]}"
    # Sanity: it's an HTML page from this app.
    assert "<html" in r.text.lower() or "verid" in r.text.lower()


@pytest.mark.parametrize("path", CORE_APIS_200)
def test_core_apis_ok(admin_client, path):
    r = admin_client.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}\n{r.text[:300]}"


@pytest.mark.parametrize("path", SOFT_GET_ROUTES)
def test_no_route_5xx(admin_client, path):
    r = admin_client.get(path)
    assert r.status_code < 500, f"{path} returned server error {r.status_code}\n{r.text[:300]}"


def test_generate_input_validation(admin_client):
    """The generate endpoint still rejects bad input (422) — not a crash."""
    r = admin_client.post(
        "/api/generate",
        json={"generation_type": "TEST_CASES", "input_text": "short", "quantity": 1},
    )
    assert r.status_code == 422


# ── Structural invariants (lock in the modular architecture) ─────────────────────

def test_expected_routes_registered():
    """All core routes exist on the app (catches accidental removal in a refactor)."""
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    for expected in [
        "/", "/projects", "/projects/{project_key}/stories", "/generate/{issue_key}",
        "/api/health", "/api/generation-types",
        "/api/jira/status", "/api/jira/projects", "/api/jira/push-xray",
        "/dashboard", "/profile", "/admin", "/login", "/setup",
    ]:
        assert expected in paths, f"route disappeared: {expected}"


def test_scaffold_packages_import():
    """The modular skeleton packages import cleanly (inert today)."""
    import importlib
    for mod in [
        "app.platform", "app.product", "app.delivery",
        "app.platform.licensing", "app.platform.knowledge", "app.platform.users",
        "app.product.generation", "app.product.integrations.jira",
        "app.product.integrations.xray", "app.delivery.webapp",
        "app.delivery.atlassian_connect",
    ]:
        importlib.import_module(mod)


def test_platform_does_not_depend_on_product_or_delivery():
    """Architecture rule: dependency direction is delivery -> product -> platform.

    platform/ must NEVER import from product/ or delivery/. This static check
    keeps the skeleton genuinely reusable as code migrates in.
    """
    platform_dir = pathlib.Path(__file__).parent.parent / "app" / "platform"
    offenders = []
    for py in platform_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "app.product" in text or "app.delivery" in text:
            offenders.append(str(py))
    assert not offenders, f"platform/ illegally imports product/delivery: {offenders}"
