# Verid-iq

**AI-Powered Test Intelligence** — by Network Logic Limited  
*AI drafts. You review. Your expertise, accelerated.*

[![CI](https://github.com/IK2025-HASH/veridiq/actions/workflows/ci.yml/badge.svg)](https://github.com/IK2025-HASH/veridiq/actions/workflows/ci.yml)

---

## What it does

Verid-iq connects to your Jira, reads your stories, and uses Claude AI to
generate professional test artifacts — test cases, BDD scenarios, negative
tests, test plans, defect reports, exploratory charters, AC reviews, and
regression impact analysis.

**Human-in-the-loop by design:** AI drafts, you review, you approve.
Each approved artifact is pushed back to Jira/Xray as its own linked issue.

---

## Quick start (Windows, local)

**One click:**
```
run.bat
```
Opens at `http://127.0.0.1:8000`. On first boot, a setup wizard asks for
your admin email, password, and Anthropic API key.

**Manual:**
```
cd veridiq-new
..\venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## Run the tests

```
pytest tests/ -q
```

Expected: **48 passed** in ~3 seconds. No network or Postgres needed —
the test suite runs against an in-memory SQLite database with fake keys.

For a full HTML + JUnit XML report:
```
test-evidence.bat
```
Opens `reports\report.html` in the browser.

---

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Jinja2 templates |
| Database | SQLite locally · PostgreSQL on Railway (auto-selected from `DATABASE_URL`) |
| AI | Anthropic Claude (`claude-sonnet-4-6`) via official SDK |
| Auth | bcrypt + JWT cookies (`python-jose`) |
| Jira integration | Jira REST API v3 (Basic auth) |

---

## Project layout

```
app/
  api/          — route handlers (web pages, Jira, generate, auth, admin)
  core/         — AI engine, Jira client, prompt templates, settings service
  templates/    — Jinja2 HTML templates
  platform/     — (scaffold) auth, billing, knowledge, licensing, users
  product/      — (scaffold) generation, Jira/Xray integrations
  delivery/     — (scaffold) Atlassian Connect, webapp
tests/
  conftest.py   — hermetic test fixtures (throwaway SQLite, fake API keys)
  test_smoke.py — end-to-end safety net (48 tests)
  test_veridiq.py — unit tests
```

---

## Key docs

| File | Purpose |
|---|---|
| [`HANDOFF.md`](./HANDOFF.md) | Single source of truth — current state, how to run, known issues |
| [`BACKLOG.md`](./BACKLOG.md) | Product backlog — 10 sprints, CI/CD plan, Definition of Done |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Modular target architecture and migration plan |
| [`CHANGELOG.md`](./CHANGELOG.md) | Release history and freeze branches |
| [`DEFECTS.md`](./DEFECTS.md) | Defect register (VRD-Dnnn) |
| [`TEST_PLAN.md`](./TEST_PLAN.md) | Test coverage map |
| [`RACI.md`](./RACI.md) | Roles and responsibilities |

---

## Freeze branches (roll back to any working state)

```
git reset --hard origin/snapshot/v0.4.0-per-item-xray   # latest stable
git reset --hard origin/snapshot/v0.3.0-smoketest
git reset --hard origin/snapshot/v0.2.0-tier12
git reset --hard origin/snapshot/v0.1.0-working
```

---

## Licence

Copyright © 2026 Network Logic Limited. All rights reserved.
