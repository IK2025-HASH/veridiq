# Verid-iq — Project Handoff / Working Context

> **Read this first.** This file is the single source of truth for picking up
> work on Verid-iq in a fresh session. It reflects the *actual current state*
> of the code — `README.md` is partly aspirational (marketplace, Postgres-only,
> Atlassian Connect) and does NOT describe what runs today. When in doubt,
> trust this file and the code over the README.

Last updated: 2026-06-03 · Current freeze: `snapshot/v0.2.0-tier12` (`ec4a6f2`)

**Companion docs:** `ARCHITECTURE.md` (folder structure, modular target, migration
plan) · `CHANGELOG.md` (release history & freeze branches).

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
- **Milestone 1 (current):** runs locally on Windows with **SQLite**. No Postgres,
  no external services required. This is what we are stabilising now.
- **Milestone 2 (not started):** same codebase deployed on **Railway** with
  **PostgreSQL**. DB is selected from `DATABASE_URL` at runtime — no code fork.

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

Manual (Command Prompt / cmd.exe):
```
cd C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new
..\venv\Scripts\activate.bat            REM use activate.bat in cmd, Activate.ps1 in PowerShell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
> Gotcha: `Activate.ps1` does nothing in cmd.exe (silent no-op). If `python -m
> uvicorn` says "No module named uvicorn", the venv isn't active — the prompt
> won't show `(venv)`. Use `activate.bat` in cmd.

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
| Shell used | **Command Prompt (cmd.exe)** — not PowerShell. Use `activate.bat`, not `Activate.ps1`. |
| Project folder | `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new` |
| Venv location | parent: `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\venv` (shared) |
| Activate (cmd) | `..\venv\Scripts\activate.bat` |
| Run command | `run.bat`  *(or)*  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| App URL (local) | http://127.0.0.1:8000 |
| Owner name | Ilyas Kadri |
| Admin login email | `ilyas@networklogic.uk` |
| Owner contact email | `ilyas.kadri@gmail.com` |
| Company | Network Logic Limited |
| Git remote | `IK2025-HASH/veridiq` (GitHub) |
| Real Jira base URL | **TBD** — never captured (transcript only had example URLs) |
| Xray installed on their Jira? | **Yes (strongly implied)** — the previous MVP pushed tests that became real Jira keys (see §3b) |

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
| `app/api/users.py` | In-memory users, auth helpers, profile/team/credits routes |
| `app/api/setup.py` | First-boot setup wizard |
| `app/core/jira_client.py` | Jira REST client |
| `app/core/ai_engine.py` | Anthropic integration, prompt building, generation types |
| `app/core/settings_service.py` | DB-backed settings, encryption, sync-in-thread |
| `app/core/auth.py` | bcrypt + JWT |
| `app/templates/web/` | Jinja2 templates (extend `_base.html`, except `index.html` which is standalone) |

---

## 6. Branch & freeze strategy
- **Develop on:** `claude/confident-maxwell-nJkvm`
- **Production:** `main`
- **Freeze points** (immutable, on origin):
  - `snapshot/v0.1.0-working` (`04da5c2`) — first working local build
  - `snapshot/v0.2.0-tier12` (`ec4a6f2`) — + project browser & per-issue page
- Roll back: `git reset --hard origin/snapshot/v0.2.0-tier12`
- **Tags don't work** on this remote (push returns HTTP 403) — use branches.

See `CHANGELOG.md` for what each release contains.

---

## 7. Known problems (open)
1. **Xray push** — reported failing ("Xray does not connect"). The exact error
   text from the **Approve & Push to Xray** button has not yet been captured, so
   root cause is unconfirmed. **Important context (§3b):** the previous MVP
   (StoryToTest) successfully pushed individual test cases to this *same* Jira and
   they became real issues (APR-30/31/32). So the Jira/Xray side works — the bug
   is in Verid-iq's push implementation (likely issue-type name, payload shape, or
   the single-blob-vs-per-card approach), NOT a missing "Test" type.
   NEXT STEP: get the literal red `✗ …` message and compare our payload to the
   StoryToTest approach (per-card create).
2. **Regular users not persisted** — only admin survives restart (Milestone-1
   in-memory `USERS`). Acceptable for now; revisit for Milestone 2.
3. README is out of date vs. actual Milestone-1 reality (see top of this file).

---

## 8. Roadmap / agreed next steps
- **Tier 3 UX (agreed, not started):** parse AI output into structured per-test-case
  cards (TC-1, TC-2 … with Preconditions / Steps / Expected), and allow pushing
  each card individually to Xray (each getting its own Jira key). Inspired by the
  "StoryToTest" PoC screenshots — inspiration, not pixel copy.
- **Milestone 2:** Railway + PostgreSQL deployment.

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
- **"Where do I run commands?"** → §3a project folder, in cmd.exe.
- **"How do I start the app?"** → `run.bat`, or manual uvicorn (§3a).
- **"Why does venv activation do nothing?"** → cmd.exe needs `activate.bat`,
  not `Activate.ps1` (silent no-op in cmd).
- **"What are the project keys?"** → APR, SCRUM (§3a).
- **"Did Xray push ever work?"** → Yes, in StoryToTest (§3b) on the same Jira.
- **"What's the model id?"** → `claude-sonnet-4-6`.
- **"What branch do we develop on / where's the freeze?"** → §6.
- **Still genuinely unknown (TBD):** real Jira base URL; the owner's full list of
  "few problems"; the end-goal (personal tool vs PoC vs sellable product).

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
