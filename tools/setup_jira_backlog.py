#!/usr/bin/env python3
"""
tools/setup_jira_backlog.py
Verid-iq development backlog creator.

Creates Epics and Stories in your Jira project based on the Verid-iq sprint plan.
Idempotent — safe to run multiple times (skips issues that already exist).

Required env vars:
    JIRA_URL          https://yourcompany.atlassian.net
    JIRA_EMAIL        your Atlassian account email
    JIRA_API_TOKEN    Atlassian API token (not your password)
    JIRA_PROJECT_KEY  project key, e.g. VRD

Optional:
    DRY_RUN=1         print what would be created without calling the API

Usage:
    pip install httpx
    export JIRA_URL=https://yourcompany.atlassian.net
    export JIRA_EMAIL=you@example.com
    export JIRA_API_TOKEN=your_token_here
    export JIRA_PROJECT_KEY=VRD
    python tools/setup_jira_backlog.py
"""

import base64
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required.  Run:  pip install httpx")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Backlog definition — mirrors BACKLOG.md
# ---------------------------------------------------------------------------
SPRINTS = [
    {
        "id": "S0",
        "theme": "Core product",
        "summary": "Sprint 0 — Core product (v0.4.0)",
        "done": True,
        "stories": [
            "8 generation types with SSE streaming",
            "Per-item Xray push — each test case becomes its own linked Jira issue",
            "48 pytest smoke + unit tests",
            "Hermetic test environment (SQLite, fake keys, session-scoped fixtures)",
            "Reproducible test evidence (pytest-html report)",
        ],
    },
    {
        "id": "S1",
        "theme": "CI/CD + Test Foundation",
        "summary": "Sprint 1 — CI/CD + Test Foundation",
        "done": False,
        "stories": [
            "S1-1: GitHub Actions CI pipeline — lint + pytest + artifact upload",
            "S1-2: Playwright skeleton + screenshot evidence on every test run",
            "S1-3: Lint & format gate in CI (ruff) — fail pipeline on lint errors",
            "S1-4: Branch protection — require CI green before merging to main",
            "S1-5: README rewrite — accurate Milestone-1 description (closes VRD-D013)",
        ],
    },
    {
        "id": "S2",
        "theme": "Deploy — Railway + PostgreSQL",
        "summary": "Sprint 2 — Deploy (Railway + PostgreSQL)",
        "done": False,
        "stories": [
            "S2-1: PostgreSQL compatibility audit — fix SQLite-isms, CI matrix",
            "S2-2: Railway deployment config — Procfile, railway.toml, health check",
            "S2-3: Alembic migrations — replace create_all() with versioned migrations",
            "S2-4: Secrets management — all secrets via Railway env vars, .env.example",
            "S2-5: Smoke test against live Railway deploy — hit /api/health in CI",
        ],
    },
    {
        "id": "S3",
        "theme": "Users & Auth",
        "summary": "Sprint 3 — Users & Auth (multi-user persistence)",
        "done": False,
        "stories": [
            "S3-1: DB-backed user model — users survive restarts (closes VRD-D012)",
            "S3-2: Registration flow — email + password + invite token",
            "S3-3: Roles — admin / qa_lead / tester with route guards",
            "S3-4: Password reset — email token, 1-hour expiry, single-use",
            "S3-5: Two-factor auth (TOTP) — QR code, backup codes, login gate",
            "S3-6: Auth tests — register/login/2FA pytest + Playwright suite",
        ],
    },
    {
        "id": "S4",
        "theme": "Licensing",
        "summary": "Sprint 4 — On-premise licence key system",
        "done": False,
        "stories": [
            "S4-1: Licence key format & offline generator script",
            "S4-2: Offline validation — signature, expiry, edition, seats (no HTTP call)",
            "S4-3: Editions & feature gating — community / professional / enterprise",
            "S4-4: Seat enforcement — login blocked when seat limit reached",
            "S4-5: Grace period & expiry UI — 14-day grace, then read-only mode",
            "S4-6: Licence tests — valid/expired/grace/wrong-sig/seat-limit pytest suite",
        ],
    },
    {
        "id": "S5",
        "theme": "Knowledge Management",
        "summary": "Sprint 5 — Knowledge Management (upload & AI-augmented generation)",
        "done": False,
        "stories": [
            "S5-1: Knowledge volume storage — upload PDF/Markdown, stored per user",
            "S5-2: Knowledge retrieval — BM25 chunk search at generation time",
            "S5-3: Knowledge-augmented prompts — inject retrieved chunks into AI prompt",
            "S5-4: Knowledge UI — admin list, upload, delete; tester read-only view",
            "S5-5: Knowledge tests — upload → retrieve → generate, empty dir graceful",
        ],
    },
    {
        "id": "S6",
        "theme": "UX / UI Polish",
        "summary": "Sprint 6 — UX / UI Polish (Tier 3 cards, landing page, mobile)",
        "done": False,
        "stories": [
            "S6-1: Tier 3 TC cards — rich structured output (type tag, priority, steps table)",
            "S6-2: Landing / marketing page — public-facing hero page",
            "S6-3: Mobile / responsive pass — nav collapses, cards stack, tappable buttons",
            "S6-4: Playwright screenshot suite — every core page, attached to CI artifact",
            "S6-5: Empty states & loading polish — skeletons, consistent error messages",
        ],
    },
    {
        "id": "S7",
        "theme": "Deeper Xray & Jira",
        "summary": "Sprint 7 — Deeper Xray (test repo view, bulk generation, execution push)",
        "done": False,
        "stories": [
            "S7-1: Xray test repository view — list existing tests per project",
            "S7-2: Push to test execution — create Xray Execution, add generated tests",
            "S7-3: Bulk backlog generation — select multiple stories, generate + push all",
            "S7-4: Deeper Jira link — show acceptance criteria alongside description",
        ],
    },
    {
        "id": "S8",
        "theme": "Atlassian Marketplace",
        "summary": "Sprint 8 — Atlassian Marketplace (Connect descriptor, OAuth, listing)",
        "done": False,
        "stories": [
            "S8-1: Atlassian Connect descriptor — atlassian-connect.json, scopes, webhooks",
            "S8-2: OAuth 2.0 (3LO) install flow — store OAuth token per tenant",
            "S8-3: Multi-tenant isolation — per-installation data, licence check per tenant",
            "S8-4: Marketplace listing content — description, screenshots, privacy/terms pages",
            "S8-5: Security review — OWASP Top 10, bandit scan, pip-audit in CI",
        ],
    },
    {
        "id": "S9",
        "theme": "Billing",
        "summary": "Sprint 9 — Billing (Stripe, credits, invoices)",
        "done": False,
        "stories": [
            "S9-1: Credits model — cost per generation type, low-credit warning banner",
            "S9-2: Stripe integration — Checkout session, webhook → credit top-up",
            "S9-3: Real invoices — PDF generation, /invoices page, download",
            "S9-4: Billing tests — mock Stripe webhook, zero-credits block, buy flow Playwright",
        ],
    },
    {
        "id": "S10",
        "theme": "Modular Migration",
        "summary": "Sprint 10 — Modular Migration (platform / product / delivery refactor)",
        "done": False,
        "stories": [
            "S10-1: Migrate core/auth.py → platform/auth/ (smoke test green throughout)",
            "S10-2: Migrate core/settings_service.py → platform/settings/",
            "S10-3: Migrate core/jira_client.py → product/integrations/jira/",
            "S10-4: Migrate core/ai_engine.py → product/generation/",
            "S10-5: Migrate api/web.py routes → delivery/webapp/",
        ],
    },
]


# ---------------------------------------------------------------------------
# Jira REST API client (synchronous, no app dependencies)
# ---------------------------------------------------------------------------
class JiraBacklogClient:
    def __init__(self, base_url: str, email: str, token: str, project_key: str):
        self.base = base_url.rstrip("/")
        self.project_key = project_key
        encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(f"{self.base}{path}", headers=self.headers, params=params or {})
            if r.status_code == 401:
                print("\nERROR: 401 Unauthorised — check JIRA_EMAIL and JIRA_API_TOKEN")
                sys.exit(1)
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, payload: dict) -> dict:
        with httpx.Client(timeout=20.0) as c:
            r = c.post(f"{self.base}{path}", headers=self.headers, json=payload)
            if r.status_code == 401:
                print("\nERROR: 401 Unauthorised — check JIRA_EMAIL and JIRA_API_TOKEN")
                sys.exit(1)
            return r

    def whoami(self) -> str:
        data = self._get("/rest/api/3/myself")
        return data.get("displayName", data.get("emailAddress", "unknown"))

    def issue_exists(self, summary_prefix: str) -> str | None:
        """Return key of first matching issue, or None."""
        escaped = summary_prefix.replace('"', '\\"')
        jql = f'project = "{self.project_key}" AND summary ~ "{escaped}" ORDER BY created ASC'
        try:
            data = self._get("/rest/api/3/search/jql", {"jql": jql, "maxResults": 1, "fields": "summary"})
            issues = data.get("issues", [])
            if issues:
                return issues[0]["key"]
        except Exception:
            pass
        return None

    def create_issue(self, summary: str, issue_type: str, description: str = "", parent_key: str | None = None) -> str | None:
        """Create an issue, return its key. Tries team-managed then classic epic-link."""
        fields: dict = {
            "summary": summary[:255],
            "issuetype": {"name": issue_type},
            "project": {"key": self.project_key},
        }
        if description:
            fields["description"] = {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
            }
        if issue_type == "Epic":
            # Epic Name field (company-managed projects) — ignored gracefully if not present
            fields["customfield_10011"] = summary[:255]

        if parent_key:
            # Team-managed: use parent field
            fields["parent"] = {"key": parent_key}

        r = self._post("/rest/api/3/issue", {"fields": fields})

        if r.status_code == 400 and parent_key:
            # Classic project: fall back to Epic Link custom field
            fields.pop("parent", None)
            fields["customfield_10014"] = parent_key
            r = self._post("/rest/api/3/issue", {"fields": fields})

        if r.status_code == 400 and issue_type == "Epic":
            # Epic Name field not supported — remove and retry
            fields.pop("customfield_10011", None)
            r = self._post("/rest/api/3/issue", {"fields": fields})

        if r.status_code not in (200, 201):
            print(f"      WARN: could not create '{summary[:60]}' — {r.status_code}: {r.text[:120]}")
            return None

        return r.json().get("key")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    jira_url   = os.environ.get("JIRA_URL", "").rstrip("/")
    jira_email = os.environ.get("JIRA_EMAIL", "")
    jira_token = os.environ.get("JIRA_API_TOKEN", "")
    project    = os.environ.get("JIRA_PROJECT_KEY", "").upper()
    dry_run    = os.environ.get("DRY_RUN", "").strip() == "1"

    missing = [k for k, v in [
        ("JIRA_URL", jira_url), ("JIRA_EMAIL", jira_email),
        ("JIRA_API_TOKEN", jira_token), ("JIRA_PROJECT_KEY", project),
    ] if not v]
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}")
        print(__doc__)
        sys.exit(1)

    print("=" * 60)
    print("  Verid-iq Jira Backlog Setup")
    print("=" * 60)
    print(f"  Jira URL    : {jira_url}")
    print(f"  Project key : {project}")
    print(f"  Dry run     : {'YES — no issues will be created' if dry_run else 'NO — creating issues'}")
    print()

    client = JiraBacklogClient(jira_url, jira_email, jira_token, project)

    if not dry_run:
        try:
            name = client.whoami()
            print(f"  Connected as: {name}")
        except Exception as e:
            print(f"ERROR: could not connect to Jira — {e}")
            sys.exit(1)
    print()

    created_epics   = 0
    skipped_epics   = 0
    created_stories = 0
    skipped_stories = 0
    results = []

    for sprint in SPRINTS:
        status_tag = " [DONE]" if sprint["done"] else ""
        print(f"── {sprint['id']}: {sprint['theme']}{status_tag}")

        epic_key = None
        epic_summary = sprint["summary"]

        if dry_run:
            print(f"   [DRY RUN] would create Epic: {epic_summary}")
            epic_key = f"{project}-???"
        else:
            existing = client.issue_exists(sprint["id"] + " —")
            if existing:
                print(f"   Epic already exists: {existing}  (skipping)")
                epic_key = existing
                skipped_epics += 1
            else:
                desc = f"{sprint['id']} | {sprint['theme']} | Verid-iq sprint backlog"
                epic_key = client.create_issue(epic_summary, "Epic", description=desc)
                if epic_key:
                    print(f"   Created Epic: {epic_key}  {epic_summary}")
                    created_epics += 1
                    results.append({"type": "Epic", "key": epic_key, "summary": epic_summary})
                    time.sleep(0.3)  # avoid Jira rate limit

        for story_summary in sprint["stories"]:
            if dry_run:
                print(f"      [DRY RUN] would create Story: {story_summary[:70]}")
                continue

            existing = client.issue_exists(story_summary[:40])
            if existing:
                print(f"      Story already exists: {existing}  (skipping)")
                skipped_stories += 1
                continue

            story_key = client.create_issue(
                story_summary, "Story",
                description=f"Part of {sprint['id']} — {sprint['theme']}. See BACKLOG.md for acceptance criteria.",
                parent_key=epic_key,
            )
            if story_key:
                short = story_summary[:65]
                print(f"      Created Story: {story_key}  {short}")
                created_stories += 1
                results.append({"type": "Story", "key": story_key, "summary": story_summary})
                time.sleep(0.2)

        print()

    if dry_run:
        print("Dry run complete — no issues were created.")
        return

    print("=" * 60)
    print(f"  Epics  created: {created_epics}   skipped (existed): {skipped_epics}")
    print(f"  Stories created: {created_stories}  skipped (existed): {skipped_stories}")
    print()
    if results:
        print("  Created issues:")
        for r in results:
            url = f"{jira_url}/browse/{r['key']}"
            print(f"    [{r['type']:5s}] {r['key']:12s}  {r['summary'][:55]}  {url}")
    print("=" * 60)
    print(f"\n  Board: {jira_url}/jira/software/projects/{project}/boards")
    print()


if __name__ == "__main__":
    main()
