# Verid-iq — Project Handoff / Working Context

> **Read this first.** This file is the single source of truth for picking up
> work on Verid-iq in a fresh session. It reflects the *actual current state*
> of the code — `README.md` is partly aspirational (marketplace, Postgres-only,
> Atlassian Connect) and does NOT describe what runs today. When in doubt,
> trust this file and the code over the README.

Last updated: 2026-06-05 · Active branch: `claude/confident-maxwell-nJkvm` · Sprints complete: S0, S3, S6

**Companion docs:** `ARCHITECTURE.md` (folder structure, modular target, migration
plan) · `CHANGELOG.md` (release history & freeze branches) · `RACI.md` (roles &
responsibilities, runtime + build) · `DEFECTS.md` (defect register) · `TEST_PLAN.md`
(what's tested + how to see it).

---

## 1. What the product is
A web app for QA / test professionals who have their **own** Jira + Xray instance.

**Core loop:**
1. User connects their own Jira (URL + email + API token).
2. They browse a Jira project → pick a story.
3. Claude AI drafts test artifacts from the story (test cases, BDD, negative
   tests, test plan, defect report, exploratory charter, AC review, regression impact).
4. **Human reviews and approves** — AI never auto-publishes.
5. Approved artifact is pushed back into Jira/Xray as a Test issue.

**Design principle:** human-in-the-loop. AI drafts, the tester decides.

**Product status & go-to-market (confirmed by owner):** this is a **full commercial
product**, not a personal tool or throwaway PoC. Planned launch on **4 surfaces**:
(1) LinkedIn — owner profile + a self-built LinkedIn community; (2) Atlassian
Marketplace (Jira Cloud app); (3) Xray Marketplace (SmartBear); (4) its own landing
page on a **subdomain of the Network Logic main domain**. This drives the modular
architecture goal — see `ARCHITECTURE.md`.

---

## 2. Milestones
- **Milestone 1 (✅ complete):** runs locally on Windows (and on-network mobile) with
  **SQLite**. Full multi-user auth (JWT, 2FA, password reset, roles), DB-backed users,
  admin panel, Jira/Xray integration, mobile-responsive UI, animated product demo,
  CI pipeline (GitHub Actions), Playwright screenshot tests. 48 unit + smoke tests green.
- **Milestone 2 (🚧 blocked — code ready):** same codebase deployed on **Railway**
  with **PostgreSQL**. `railway.toml` is configured; alembic migrations in place.
  `DATABASE_URL` selects the DB at runtime — no code fork. **Blocked by:** Railway
  trial expired (needs Hobby plan, ~$5/month) and a US West Private Networking incident
  at time of first attempt. Resume when Railway issue resolves and plan is upgraded.

**Distribution modes (one codebase):** SaaS (Network Logic hosts) AND **on-premise
instance licence** (customer hosts; access via a signed, offline-validated licence
key). This drives the `platform/licensing/` module. Owner also requires first-class
**User Management**, **Knowledge Management**, and a **RACI** (see `RACI.md`).
Architecture & module specs: `ARCHITECTURE.md` + each module's `README.md`.

---

## 3. How to run locally (Windows) — verified
**Project folder:** `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new`
**Venv:** shared from the parent folder `veridiq-export\venv`.

Easiest — one click:
```
run.bat
```
`run.bat` creates the venv if missing, installs `requirements.txt`, and launches
uvicorn at http://127.0.0.1:8000.

Manual (Command Prompt):
```
cd C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new
..\venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mobile testing (same WiFi — phone can reach `http://192.168.0.10:8000`):
```
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
> Find your IP: `ipconfig` → Wireless LAN adapter Wi-Fi → IPv4 Address.
> First run may need a Windows Firewall "Allow access" prompt (or add the rule manually).

> Gotcha: `Activate.ps1` does nothing in cmd.exe (silent no-op). If `python -m
> uvicorn` says "No module named uvicorn", the venv isn't active — the prompt
> won't show `(venv)`. Use `activate.bat` in cmd; `Activate.ps1` in PowerShell.

> Gotcha: the folder is under **OneDrive**, which can lock/sync files mid-write.
> Odd file-permission or lock errors are usually OneDrive, not the code.

First boot shows a **setup wizard** (`/setup`): set admin email, password, and
paste the Anthropic API key. After setup, log in and connect Jira at
`/profile#jira`.

---

## 3a. Canonical environment & identity facts (do NOT re-ask)
These are confirmed. If a value is `TBD`, it is genuinely unknown — fill it when
provided; do not pester the owner for already-recorded values.

| Fact | Value |
|---|---|
| Operating system | Windows |
| Shell used | Uses both **cmd.exe** and **PowerShell**. Use `activate.bat` in cmd; `Activate.ps1` in PS. |
| Project folder | `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new` |
| Venv location | parent: `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\venv` (shared) |
| Activate (cmd) | `..\venv\Scripts\activate.bat` |
| Activate (PS) | `..\venv\Scripts\Activate.ps1` |
| Run command (local) | `run.bat`  *(or)*  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Run command (mobile) | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| App URL (local) | http://127.0.0.1:8000 |
| App URL (mobile, same WiFi) | http://192.168.0.10:8000 (laptop IP confirmed via `ipconfig`) |
| Owner name | Ilyas Kadri |
| Admin login email | `ilyas@networklogic.uk` |
| Owner contact email | `ilyas.kadri@gmail.com` |
| Company | Network Logic Limited |
| Git remote | `IK2025-HASH/veridiq` (GitHub) |
| DNS provider | 123-reg (for `networklogic.uk` domain) |
| Real Jira base URL | **TBD** — never captured in transcript |
| Xray installed on their Jira? | **Yes (confirmed)** — APR-101/102/103 pushed and linked to APR-42 in this session's demo |
| Railway plan | Trial expired — needs Hobby plan ($5/month) before M2 deployment |
| Local version snapshots | `versions/` folder: `v1.3.0-s3-users` (runnable archive, no .git or .db) |

### Their Jira instance (observed in screenshots)
| Project key | Name | Notes |
|---|---|---|
| `APR` | Abusive Payment Reference | ~23 issues; stories APR-22…APR-28 are "To Do", Medium |
| `SCRUM` | story2testdemo | demo project |
| Sample story | `APR-28` — "Scalability for peak load" | "System must handle peak transaction volumes without degradation." |

---

## 3b. Previous MVP — "StoryToTest" (the UX target & a working-Xray proof)
Before Verid-iq, the owner built a previous MVP called **StoryToTest** (same Jira
account, branding "Proof of Concept — Built by Ilyas Kadri", indigo/amber theme).
Its screenshots are the **inspiration** for the current UX work (Tier 1–3) — they
are a reference for the *journey*, NOT a pixel-for-pixel copy. The Verid-iq look
(navy/teal, Network Logic branding) stays.

**StoryToTest user journey (the target we're rebuilding in Verid-iq):**
1. Landing → "Turn Jira Stories into Test Cases. Instantly." → Browse Projects / Connect Jira.
2. `/projects` — project cards (APR, SCRUM).
3. `/projects/APR/stories` — backlog table (Key, Summary, Type, Status, Priority) with a **Generate** button per row.
4. `/generate/APR-28` — left: story context; right: **structured test-case cards**.

**What StoryToTest did that Verid-iq does NOT yet (this is Tier 3):**
- Output rendered as **individual test-case cards** — `TC-1`, `TC-2`, …, each with:
  a coloured **type** tag (Positive / Negative / Edge), a **priority** tag (High…),
  Description, **Preconditions**, numbered **Steps** (Action + Expected), and
  **Expected Outcome**.
- Per-card actions and a **"Push All to Xray"** button.
- **CRITICAL PROOF:** each pushed test case became its **own Jira issue with its own
  key** — observed: `APR-28` (story) → generated 8 cases → pushed as **APR-30,
  APR-31, APR-32 …**, each card showing "✓ Pushed to Xray as APR-3x" and linked
  back to the story. **So creating test issues on this Jira works** — Verid-iq's
  current single-blob push failing is an *implementation gap in Verid-iq*, not a
  limitation of the owner's Jira/Xray.

This reframes the Xray problem (see §7): we have a known-good precedent to match.

---

## 4. Tech stack & non-obvious decisions
- FastAPI + Jinja2 templates + SQLAlchemy 2.0 + Anthropic SDK.
- **DB:** SQLite (`aiosqlite`) locally, PostgreSQL (`asyncpg`) on Railway,
  chosen from `DATABASE_URL` in `config.py`.
- **greenlet avoidance (Windows):** every DB operation runs through
  `asyncio.to_thread` with a *synchronous* SQLAlchemy engine. Do NOT introduce
  async-engine DB calls on the request path — it reintroduces the greenlet crash.
  See `core/settings_service.py` and `database.py`.
- **Auth:** direct `bcrypt` (NOT passlib — passlib crashes with bcrypt ≥4.1).
  JWT cookies via `python-jose`. See `core/auth.py`.
- **Users are in-memory** (`api/users.py` `USERS` dict) for Milestone 1. Only the
  **admin** is persisted (to the settings table) and restored on startup. Regular
  registered users do NOT survive a restart yet — a Milestone-2 item.
- **Settings + secrets:** stored in the `app_settings` DB table. Sensitive keys
  are Fernet-encrypted at rest. Encrypted keys: `anthropic_api_key`,
  `smtp_password`, `linkedin_client_secret`, and any `jira_api_token__*`.
- **Model id:** `claude-sonnet-4-6` (config default). The old dated id 404'd.
- **Jira API:** Basic auth (email:token base64). Use `/rest/api/3/search/jql`
  for issues — the old `/rest/api/3/search` returns **410 Gone**. Projects via
  `/rest/api/3/project/search`. ADF↔text helpers live in `core/jira_client.py`.

---

## 5. Key files
| File | Role |
|---|---|
| `app/main.py` | App entry, lifespan: create tables, restore admin + Jira creds |
| `app/config.py` | Settings, DB url, model id |
| `app/api/web.py` | Page routes (`/`, `/projects`, `/projects/{k}/stories`, `/generate/{key}`) |
| `app/api/jira.py` | Jira connect/disconnect/status, projects, issues, push-xray |
| `app/api/generate.py` | AI generation endpoints (SSE stream + non-stream) |
| `app/api/users.py` | DB-backed users, auth helpers, profile/team/credits routes |
| `app/api/setup.py` | First-boot setup wizard |
| `app/core/jira_client.py` | Jira REST client |
| `app/core/ai_engine.py` | Anthropic integration, prompt building, generation types |
| `app/core/settings_service.py` | DB-backed settings, encryption, sync-in-thread |
| `app/core/auth.py` | bcrypt + JWT + 2FA (TOTP) |
| `app/core/user_repository.py` | SQLAlchemy user CRUD (write-through cache: USERS dict + DB) |
| `app/templates/web/_base.html` | Base layout: sticky nav, mobile hamburger menu, footer |
| `app/templates/web/index.html` | Standalone homepage: animated 4-stage demo + AI generator |
| `app/templates/web/generate_issue.html` | Per-issue generation page with Tier 3 TC cards |
| `app/templates/web/` | All other Jinja2 templates (extend `_base.html`) |
| `.github/workflows/ci.yml` | GitHub Actions: Job 1 = lint + 48 unit tests; Job 2 = Playwright screenshots |
| `tests/test_playwright.py` | 7 browser tests (live uvicorn fixture) → screenshots to `screenshots/` |
| `tests/test_smoke.py` | End-to-end safety net (boots app, 48 tests) |
| `tools/setup_jira_backlog.py` | Standalone script: create 10-sprint backlog in Jira (DRY_RUN=1 for preview) |
| `railway.toml` | Railway start command: alembic upgrade → uvicorn |
| `versions/v1.3.0-s3-users/` | Runnable local archive of the Sprint 3 freeze (no .git, no .db) |

---

## 6. Branch & freeze strategy
- **Develop on:** `claude/confident-maxwell-nJkvm`
- **Production:** `main`
- **Freeze points** (immutable, on origin):
  - `snapshot/v0.1.0-working` (`04da5c2`) — first working local build
  - `snapshot/v0.2.0-tier12` (`ec4a6f2`) — + project browser & per-issue page
  - `snapshot/v0.4.0-per-item-xray` (`bd99710`) — per-item Xray push, 48 tests
  - `sprint/s3-users` — Sprint 3 complete: DB-backed users, 2FA, password reset, roles
  - *(planned)* `snapshot/v1.6.0-ux-polish` — Sprint 6 complete (create at next milestone)
- **Local version archives** (in `versions/` on user's machine, gitignored):
  - `versions/v1.3.0-s3-users/` — clean runnable copy after Sprint 3
- Roll back to any freeze: `git fetch origin <branch> && git reset --hard origin/<branch>`
- **Tags don't work** on this remote (HTTP 403) — use branches instead.

See `CHANGELOG.md` for what each release contains.

---

## 6a. Tests / safety net
- `tests/test_smoke.py` — **step-0 smoke test** (the EVOLVE-NEVER-BREAK net): boots
  the app, runs first-boot setup, asserts the core journey + platform pages render
  (no 5xx), validates input handling, and enforces structural invariants (expected
  routes present; scaffold packages import; `platform/` never imports `product/` or
  `delivery/`). Run green before AND after every refactor step.
- `tests/conftest.py` — pins the suite to a throwaway **SQLite** DB + fake keys
  (set before app import). No Postgres/network needed.
- `tests/test_playwright.py` — **7 Playwright browser tests** (live uvicorn process,
  session-scoped fixture). Covers: landing, login, register, homepage desktop + mobile,
  hamburger menu, terms. Screenshots written to `screenshots/` (gitignored).
  Run separately: `playwright install chromium && pytest tests/test_playwright.py --browser chromium -v`
- **48 unit + smoke tests** green as of Sprint 6. Run with: `pytest tests/ --ignore=tests/test_playwright.py -q`
- **CI (GitHub Actions):** `.github/workflows/ci.yml` — two jobs run on every push:
  Job 1 = ruff lint + 48 unit tests (uploads `report.html`).
  Job 2 = Playwright tests (uploads `screenshots/` as artifact).
- **Bugs the smoke test caught immediately:** `/team` and `/invoices` were linked in
  the nav but their templates didn't exist → **500 in production**. Fixed by adding
  `web/team.html` and `web/invoices.html`.

## 7. Known problems (open)
> Canonical list with severities is in **`DEFECTS.md`**. Below is the current short form.

1. **~~Xray push failing~~** — **FIXED** (VRD-D011). Per-item push was implemented in
   v0.4.0 and verified: APR-101/102/103 were pushed and linked to APR-42 in demo.
   Each generated test case now gets its own Jira issue + its own Push button.
2. **~~Regular users not persisted~~** — **FIXED** (VRD-D012). Sprint 3 made users
   fully DB-backed via `user_repository.py`. Write-through cache: `USERS` dict
   (fast reads) + every write persists to DB. All users survive restart.
3. **README out of date** (VRD-D013) — still open (S4 Low). `HANDOFF.md` is the
   source of truth. README rewrite planned once modular migration stabilises.
4. **Milestone 2 deploy blocked** — see §2. No code issue; purely a Railway
   plan/infrastructure blocker. Resume when plan upgraded.
5. **S6-2 landing page** — partially done (login-aware nav, "Start free"/"Dashboard"
   CTAs). Full marketing copy ("Turn Jira Stories into Test Cases. Instantly.") and
   feature highlights section not yet built.

---

## 8. Roadmap / agreed next steps

**Completed this session:**
- ✅ Tier 3 TC cards (S6-1) — structured output with Priority, Test Type, Steps table, Outcome
- ✅ Mobile-responsive nav (S6-3) — hamburger menu, mobile drawer, 44px tap targets
- ✅ Playwright screenshot suite (S6-4) + GitHub Actions CI pipeline
- ✅ Empty states & loading skeletons (S6-5)

**Immediate next (in priority order):**
1. **Milestone 2 deploy** (S2) — resume when Railway Hobby plan is purchased.
   Code is ready; run `git push` to Railway and the `railway.toml` handles the rest.
2. **S6-2 landing page** — complete the marketing content at `/landing`:
   headline, feature highlights, proof points, CTA buttons.
3. **Sprint 4 — Licensing** — on-prem licence key system (needed for Marketplace).
4. **Sprint 7 — Deeper Xray** — bulk generation, test execution push.
5. **Sprint 8 — Marketplace** — Atlassian Connect descriptor, OAuth 2.0 install flow.

---

## 9. Open questions for the product owner (Ilyas)
These were raised and parked — answer before large new work:
1. **The "few problems"** beyond the known Xray issue — to be listed.
2. ~~**End goal**~~ — **ANSWERED:** full commercial product, 4 launch surfaces
   (LinkedIn community, Atlassian Marketplace, Xray Marketplace, Network Logic
   subdomain). See §1 and `ARCHITECTURE.md`.

### Agreed direction: modular skeleton
Owner wants the folder structure evolved to be **modular** (reduce risk of breaking
unrelated things) and **reusable as a skeleton for other products**. Target
architecture and an incremental, freeze-per-step migration plan are captured in
`ARCHITECTURE.md` §3–§4. **Not started** — awaiting go-ahead; a boot/route smoke
test is the prerequisite (step 0).

---

## 9a. Do-not-re-ask glossary
Quick answers to things that have been asked/derived before. Check here before
asking the owner anything:
- **"Where do I run commands?"** → §3a project folder. User uses both cmd.exe and PowerShell.
- **"How do I start the app?"** → `run.bat` (desktop only), or `uvicorn --host 0.0.0.0 --port 8000` for mobile too (§3).
- **"How do I access from mobile?"** → Same WiFi, `http://192.168.0.10:8000`. Run with `--host 0.0.0.0`.
- **"Why does venv activation do nothing?"** → In cmd.exe use `activate.bat`; in PowerShell use `Activate.ps1`.
- **"What are the project keys?"** → APR, SCRUM (§3a).
- **"Did Xray push ever work?"** → Yes — both in StoryToTest (APR-30/31/32) AND in current Verid-iq (APR-101/102/103 pushed to APR-42).
- **"What's the model id?"** → `claude-sonnet-4-6`.
- **"What branch do we develop on?"** → `claude/confident-maxwell-nJkvm` (§6).
- **"Are users persisted across restart?"** → Yes — Sprint 3 made all users DB-backed (VRD-D012 fixed).
- **"Is the hero section on the homepage?"** → No — removed (commit `63d2788`). Animated 4-stage demo is the first section. If still visible, do `git reset --hard origin/claude/confident-maxwell-nJkvm` + hard-refresh.
- **"What's the DNS provider?"** → 123-reg for `networklogic.uk`.
- **"How do I run Playwright tests?"** → `playwright install chromium && pytest tests/test_playwright.py --browser chromium -v`
- **"Where are test screenshots?"** → `screenshots/` folder (gitignored; also uploaded as CI artifact).
- **Still genuinely TBD:** real Jira base URL (never captured in transcript).

---

## 10. Hard constraints (do not violate)
- Python stack only. No external services beyond the user's own Jira/Anthropic.
- SQLite locally / PostgreSQL on Railway — same code, no fork.
- Never commit secrets (Anthropic key, Jira tokens) to the repo or commit messages.
- Additive changes preferred; freeze before risky work so we can always roll back.
- Run/test code before claiming it works.
- **EVOLVE, NEVER BREAK (rock-carved, owner directive 2026-06-03):** the codebase
  may move toward the modular target (`ARCHITECTURE.md` §3), but ONLY through small,
  incremental, behaviour-preserving steps, each behind its own freeze branch with
  the smoke test green. **No big-bang reorganization. Never leave the repo in a
  broken state** — on GitHub, on the laptop, or on any host. If a step can't be
  done without risking a working state, stop and check with the owner first.
