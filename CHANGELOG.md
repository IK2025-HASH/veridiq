# Changelog & Release History

All notable changes to Verid-iq, newest first.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

**Freeze points** are immutable snapshot branches on the remote. To roll back to any
of them: `git reset --hard origin/<snapshot-branch>`.

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
