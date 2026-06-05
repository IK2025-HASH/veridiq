# Changelog & Release History

All notable changes to Verid-iq, newest first.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

**Freeze points** are immutable snapshot branches on the remote. To roll back to any
of them: `git fetch origin <branch> && git reset --hard origin/<branch>`.

---

## [1.6.0] — 2026-06-05 · Sprint 6 UX Polish
**Branch:** `claude/confident-maxwell-nJkvm` · **Commit:** `bb76cd6`
*(freeze branch `snapshot/v1.6.0-ux-polish` to be created at next milestone)*

### Added
- **Tier 3 TC cards (S6-1):** AI output parsed into rich structured cards. Each Test
  Case card shows a colour-coded priority badge (Critical/High/Medium/Low), test-type
  chip (Functional/Negative/Boundary/Integration), collapsible preconditions, a Steps
  table with Action + Expected Result columns, and an Expected Outcome highlight block.
  Fallback to raw `<details>` for BDD/Charters types.
- **Mobile hamburger nav (S6-3):** `_base.html` updated — desktop links hidden on
  `< md` breakpoint; animated ☰/✕ hamburger button shown on mobile; full-width
  mobile drawer with user identity, all nav links (44px tap targets), and sign-out.
- **Playwright screenshot suite (S6-4):** `tests/test_playwright.py` (7 browser tests
  — landing, login, register, homepage desktop+mobile, hamburger toggle, terms).
  `playwright==1.44.0` + `pytest-playwright==0.5.0` added to requirements.txt.
- **GitHub Actions CI pipeline (S6-4/S1):** `.github/workflows/ci.yml` — Job 1:
  ruff lint + 48 unit tests (uploads `report.html`); Job 2: Playwright tests
  (uploads `screenshots/` artifact). Triggers on push to `main`, `claude/*`, `sprint/*`.
- **Empty states & loading skeletons (S6-5):**
  - Dashboard: "No activity yet" state now has icon, message, and "Generate something →" CTA.
  - Projects page: spinner replaced with animated 6-card skeleton grid; no-projects
    state has icon, message, and "Check Jira settings →" link.
  - Stories page: spinner replaced with animated 8-row skeleton table; no-issues
    state has icon, message, and back-to-projects link.
- **Homepage animated demo:** 4-stage auto-advancing walkthrough (Paste story →
  Generating → Review cards → Pushed to Xray). Stage indicators, progress bar,
  Back/Next controls. Self-contained `<style>` + `<script>`.
- **Hero section removed:** "AI drafts. You review." text block removed from homepage;
  animated demo is now the above-the-fold content.
- **UX fixes (between sprints):** landing page now login-aware (shows "Dashboard →"
  when signed in); character counter corrected 5000 → 50000; sign-in / get-started
  buttons shown in nav when logged out.

### Notes
- Mobile access confirmed: `uvicorn --host 0.0.0.0 --port 8000`, open `http://192.168.0.10:8000` on phone.
- S6-2 (landing page marketing content) partially done — nav is login-aware; full
  copy/feature-highlights section still pending.

---

## [1.3.0] — 2026-06-04 · Sprint 3 — Full User Management & Auth
**Freeze branch:** `sprint/s3-users` · **Local archive:** `versions/v1.3.0-s3-users/`

Complete multi-user system. All users now persist across restarts. Full auth suite:
registration, login, 2FA, password reset, roles, admin panel.

### Added
- **DB-backed users (S3-1):** `user_repository.py` — SQLAlchemy CRUD with a
  write-through cache (`USERS` in-memory dict + every write persisted to DB).
  Closes VRD-D012: all users survive restart. Admin and Jira credentials restored on startup.
- **Registration flow (S3-2):** `/auth/register` — email + password + email
  verification. Admin can view and manage users at `/admin/users`.
- **Roles (S3-3):** `admin`, `qa_lead`, `tester`. `user.is_admin` guards on admin
  routes. Admin UI shows role column; admin can promote/demote users.
- **Password reset (S3-4):** `/auth/forgot-password` + `/auth/reset-password/{token}`.
  Reset token expires in 1 hour; single-use.
- **2FA — TOTP (S3-5):** `/security` page with QR code generation via `pyotp`.
  Login prompts for TOTP code when 2FA is enabled. Backup codes generated on setup.
- **Admin tooling:** `tools/setup_jira_backlog.py` — standalone script to create
  the 10-sprint product backlog in Jira (DRY_RUN=1 for preview; idempotent).

### Fixed
- VRD-D012 — Non-admin users not persisted across restart. **Verified.**

### Notes
- 48 unit + smoke tests green.

---

## [0.4.0] — 2026-06-03 · Per-item Xray push + error handling
**Freeze branch:** `snapshot/v0.4.0-per-item-xray` · **Commit:** `a9a733c`

Each AI-generated test case / scenario / charter is now its own Jira issue.
Error messages are readable. Long Jira descriptions no longer block generation.

### Fixed
- **Xray push was one big blob** — all test cases pushed into a single Jira issue
  description. Now batch types (`Test Cases`, `BDD Scenarios`, `Negative Test Cases`,
  `Exploratory Charters`) are parsed after generation into individual cards, each
  with its own **Push** button. `Push All` pushes them sequentially and shows
  live progress (`Pushing 2/5…`). Each issue is linked back to the source story.
- **`[object Object]` error on generation** — FastAPI 422 validation errors returned
  an array which the browser stringified to `[object Object]`. Added a `readError()`
  helper that turns 422 arrays, plain strings, rate-limit shapes, and anything else
  into a readable message. Applied to the generate path and both push paths.
- **5000-character input limit blocked long Jira descriptions** — issues whose
  description contained a full test-case document (e.g. APR-38) exceeded the limit
  and generation never started. Raised `max_length` from 5 000 → 50 000 characters.

### Added
- **"Open your Xray board ↗" link** after Push All — links to the project's Jira
  issue list filtered to that project, newest first. URL is captured from the
  first created issue so it adapts to any Jira site automatically.
- **Test-evidence reporting** (`test-evidence.bat`, `pytest-html==4.1.1`) — one-click
  HTML + JUnit XML test report generation (gitignored `reports/`).

### Notes
- 48 smoke + unit tests green.
- Single-doc types (Test Plan, Defect Report, AC Review, Regression Impact) retain
  the original single-push flow unchanged.

---

## [0.3.0] — 2026-06-03 · Step-0 smoke test + modular scaffold
**Freeze branch:** `snapshot/v0.3.0-smoketest` · **Commit:** `8d4c1bc`

The EVOLVE-NEVER-BREAK safety net, the additive modular skeleton, and the
project-handoff docs.

### Added
- **Smoke test** (`tests/test_smoke.py`) + `tests/conftest.py` (hermetic SQLite):
  boots the app, runs setup, asserts the core journey + platform pages render
  (no 5xx), and enforces structural invariants (routes present, scaffold imports,
  `platform/` ↛ `product/`/`delivery/`). 48 tests green.
- **Additive modular skeleton:** `app/platform/`, `app/product/`, `app/delivery/`
  (empty packages + README specs) alongside untouched working code.
- New platform module specs: `licensing/` (on-prem licence keys/seats/gating),
  `knowledge/`, `users/`.
- Docs: `HANDOFF.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `RACI.md`.

### Fixed
- `/team` and `/invoices` were linked in the nav but had **no templates → 500 in
  production**. Added `web/team.html` and `web/invoices.html` (caught by the smoke test).

### Notes
- On-premise instance-licence distribution recorded as a first-class requirement.
- No existing code moved; migration into the skeleton is incremental/freeze-per-step.

---

## [0.2.0] — 2026-06-02 · Project browser + per-issue generate page
**Freeze branch:** `snapshot/v0.2.0-tier12` · **Commit:** `ec4a6f2`

Additive UX overhaul (Tier 1 + Tier 2). Nothing in the existing flow was changed
or removed — the single-page generator at `/` still works exactly as before.

### Added
- `/projects` — project card grid, loaded from the existing Jira API.
- `/projects/{key}/stories` — backlog table with a **Generate** button per row.
- `/generate/{issue_key}` — dedicated, issue-centric generation page:
  - Left panel: Jira story context (summary, description, type, status).
  - Right panel: generation-type picker → streaming SSE output → Approve & Push to Xray.
  - Breadcrumb: Projects › {project} › Backlog › {issue}.
  - Xray push pre-fills project key + test title from the issue.
- Landing hero (`index.html`) gains **Browse Projects** / **Quick Generate** CTAs (logged-in only).
- `_base.html` gains an overridable `{% block main_class %}` (defaults to `max-w-5xl`)
  so wide pages can opt into a larger container.

### Notes
- All new pages call existing `/api/*` endpoints; no API changes.

---

## [0.1.0] — 2026-06-01 · First working local build
**Freeze branch:** `snapshot/v0.1.0-working` · **Commit:** `04da5c2`

The first end-to-end working state on Windows + SQLite. This is the stable base.

### Fixed
- **AI 404 error:** model id `claude-sonnet-4-20250514` did not exist →
  corrected to `claude-sonnet-4-6` (`config.py`). This was the cause of
  "AI service error (404)" on generate.
- **Jira credentials lost on every restart:** credentials lived only in the
  in-memory `USERS` dict. Now saved to the DB on connect (`jira.py`) and
  restored on startup (`main.py`). The Jira API token is encrypted at rest.
- **The real 500 on setup/login:** `passlib==1.7.4` crashes with `bcrypt>=4.1`
  (its self-test raises on >72-byte passwords). Replaced passlib with direct
  `bcrypt` usage (`core/auth.py`). This was the root cause of every "Internal
  Server Error" — found by actually running the server, not by guessing.
- `create_session()` was called with 2 args but needs 3 (`user_agent`).

### Added
- Consistent top navigation on the Generate page (`/`) matching every other page.
- `run.bat` — one-click Windows launcher (creates venv, installs deps, runs uvicorn).
- `pydantic[email]` in requirements (EmailStr needs `email-validator`; a fresh
  install would otherwise crash on startup).

---

## Pre-0.1.0 — Foundation (2026-05-28 → 2026-06-01)
Not individually frozen; rolled into 0.1.0.

- Jira + Xray integration: list projects, list issues, import, push approved tests.
- Jira issue list **410 Gone** fix — Atlassian deprecated `/rest/api/3/search`;
  switched to `/rest/api/3/search/jql`.
- Jira project + issue pickers (browse instead of typing issue keys).
- **greenlet elimination on Windows:** all SQLAlchemy work runs via
  `asyncio.to_thread` with a *sync* engine (`settings_service.py`, `database.py`).
- SQLite for local dev, PostgreSQL for Railway — chosen from `DATABASE_URL`.
- Cross-DB SQL: `CURRENT_TIMESTAMP` instead of SQLite-only `datetime('now')`.
- Fernet encryption for sensitive settings stored in the DB.
- Admin setup wizard — API keys configured via UI, no `.env` editing.
- Admin user persisted to DB and restored on restart.

---

## Versioning & freeze convention
- Working branch: `claude/confident-maxwell-nJkvm` (active development).
- Production branch: `main`.
- Each freeze = a `snapshot/vX.Y.Z-label` branch pushed to origin.
- **Tags are NOT used** — this remote rejects tag pushes (HTTP 403). Use branches.
