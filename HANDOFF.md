# Verid-iq — Project Handoff / Working Context

> **Read this first.** This file is the single source of truth for picking up
> work on Verid-iq in a fresh session. It reflects the *actual current state*
> of the code — `README.md` is partly aspirational and does NOT describe what
> runs today. When in doubt, trust this file and the code over the README.

Last updated: 2026-06-05 · Active branch: `claude/confident-maxwell-nJkvm` · Latest commit: see below (docs update)

**Companion docs:** `CHANGELOG.md` (release history & freeze branches) · `DEFECTS.md` (defect register) · `TEST_PLAN.md` (what's tested + how to see it) · `BACKLOG.md` (sprint plan)

---

## 1. What the product is

A web app for QA / test professionals who have their **own** Jira + Xray instance.

**Core loop:**
1. User connects their own Jira (URL + email + API token).
2. They browse a Jira project → pick a story.
3. Claude AI drafts test artifacts from the story (Test Set, BDD, negative tests, test plan, defect report, exploratory charter, AC review, regression impact).
4. **Human reviews, edits (inline), and approves** — AI never auto-publishes.
5. Approved artifacts pushed to Jira/Xray: each test case becomes a proper Xray **Test** issue; if "Test Set" type selected, a Xray **Test Set** issue is created and tests linked to it.

**Design principle:** human-in-the-loop. AI drafts, the tester decides.

**Product status:** full commercial product targeting 4 surfaces: (1) LinkedIn community, (2) Atlassian Marketplace, (3) Xray Marketplace, (4) Network Logic subdomain.

---

## 2. Milestones

- **Milestone 1 (✅ complete):** runs locally on Windows (and on-network mobile) with SQLite. Full multi-user auth, DB-backed users, admin panel, Jira/Xray integration, mobile-responsive UI, animated demo, CI pipeline (GitHub Actions), Playwright tests. 48 tests green.
- **Milestone 2 (🚧 blocked — code ready):** Railway + PostgreSQL deployment. `railway.toml` configured; alembic migrations in place. **Blocked by:** Railway trial expired (needs Hobby plan ~$5/month). Resume when plan upgraded.

---

## 3. How to run locally (Windows) — verified

**Project folder:** `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new`
**Venv:** `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\venv` (shared parent)

```powershell
# Pull latest first (ALWAYS do this at start of new session)
git pull origin claude/confident-maxwell-nJkvm

# Activate venv (PowerShell)
..\venv\Scripts\Activate.ps1

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Browser: **http://127.0.0.1:8000** (or http://192.168.0.10:8000 from phone on same WiFi)

> **OneDrive gotcha:** folder is under OneDrive which can lock files mid-write. Odd permission errors are usually OneDrive sync, not the code.

> **Branch gotcha:** ALWAYS verify you are on `claude/confident-maxwell-nJkvm` before starting work. `git branch` shows current branch. If git checkout fails with "needs merge" errors, run `git reset --hard HEAD` first.

---

## 3a. Canonical environment facts (do NOT re-ask)

| Fact | Value |
|---|---|
| OS | Windows |
| Shell | Both cmd.exe AND PowerShell. Use `activate.bat` in cmd; `Activate.ps1` in PS. |
| Project folder | `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\veridiq-new` |
| Venv | `C:\Users\Ilyas\OneDrive\Projects\veridiq-export\venv` |
| App URL (local) | http://127.0.0.1:8000 |
| App URL (mobile) | http://192.168.0.10:8000 |
| Owner | Ilyas Kadri · ilyas.kadri@gmail.com |
| Admin login | ilyas@networklogic.uk |
| Company | Network Logic Limited |
| Git remote | `IK2025-HASH/veridiq` (GitHub) |
| Jira instance | ilyaskadri.atlassian.net |
| Xray installed | ✅ Yes (confirmed — APR-43 Test Set, APR-47 Test issues created this session) |
| Jira project keys | APR (Abusive Payment Reference), SCRUM (story2testdemo) |
| Sample story | APR-28 — "Scalability for peak load" |
| Railway plan | Trial expired — needs Hobby plan ($5/month) before M2 |
| DNS provider | 123-reg for networklogic.uk |
| AI model | `claude-sonnet-4-6` |

---

## 4. Tech stack

- FastAPI + Jinja2 + SQLAlchemy 2.0 async + Anthropic SDK
- SQLite (`aiosqlite`) locally / PostgreSQL (`asyncpg`) on Railway via `DATABASE_URL`
- **greenlet avoidance (Windows):** all DB ops use `asyncio.to_thread` with sync engine — do NOT introduce async-engine DB calls
- **Auth:** direct `bcrypt` (NOT passlib — crashes with bcrypt ≥4.1). JWT cookies via `python-jose`
- Settings/secrets in `app_settings` DB table; sensitive keys Fernet-encrypted at rest
- Users: write-through cache (`USERS` dict + `user_repository.py` → DB)

---

## 5. Key files

| File | Role |
|---|---|
| `app/main.py` | App entry, lifespan: create tables, restore admin + Jira creds |
| `app/api/web.py` | Page routes — `/` redirects logged-in users to `/dashboard`; `/generate/{key}` is the main generate page |
| `app/api/jira.py` | Jira endpoints incl. `push-xray`, `push-test-set`, `link-tests-to-set` |
| `app/api/generate.py` | AI generation SSE stream endpoint |
| `app/core/jira_client.py` | Jira REST client — `create_xray_test`, `create_test_set`, `add_tests_to_set`, `_push_xray_steps` |
| `app/core/ai_engine.py` | Anthropic integration, generation types, labels, icons |
| `app/templates/web/_base.html` | Base layout: nav (Generate → /projects), mobile hamburger |
| `app/templates/web/generate_issue.html` | **Main generate page** — TC cards, Edit/Save/Cancel, Test Set checkbox, Text/CSV/JSON download |
| `app/templates/web/index.html` | Public marketing/demo homepage (unauthenticated only) |
| `.github/workflows/ci.yml` | CI: ruff lint + 48 unit tests + Playwright screenshots |
| `tests/test_smoke.py` | 48 smoke + unit tests — run before and after every change |

---

## 6. Branch & freeze strategy

- **Develop on:** `claude/confident-maxwell-nJkvm`
- **Freeze branches** (immutable on origin):
  - `snapshot/v0.4.0-per-item-xray` — per-item Xray push, 48 tests
  - `sprint/s3-users` — DB-backed users, 2FA, password reset
  - `snapshot/v1.6.0-ux-polish` — Sprint 6 complete (TC cards, mobile nav, CI, empty states)
- Roll back: `git fetch origin <branch> && git reset --hard origin/<branch>`
- Tags don't work on this remote (HTTP 403) — use branches instead

**To create a new freeze before risky work:**
```powershell
git checkout -b snapshot/vX.Y.Z-description
git push -u origin snapshot/vX.Y.Z-description
git checkout claude/confident-maxwell-nJkvm
```

---

## 7. Current feature state (v1.7.x as of 2026-06-05)

### Working ✅
- **Generate flow:** Projects → Stories → Generate page (`/generate/{issue_key}`)
- **Nav:** "Generate" link → `/projects`; `/` for logged-in users → redirects to `/dashboard`
- **Test Set button:** generates test cases; auto-checks "Group into Test Set" checkbox
- **Inline card edit:** Edit/Save/Cancel on each TC card; re-parses content after save
- **Download formats:** Text (plain), CSV (with Test Set column + manual key input), JSON
- **Push individual card:** Push button per card → creates Xray Test issue + links to story
- **Push All with Test Set:** creates Test Set issue first → pushes all TCs → links them
- **Jira issue fields:** Preconditions and expected outcome go to description; steps pushed to Xray Test Details via `POST /rest/raven/1.0/api/test/{key}/step`

### Partially working ⚠️ (next thread should verify and fix)
- **Test steps in Xray Test Details:** API call is made (`_push_xray_steps`) with both `{"step":...}` and `{"action":...}` formats. **Not yet confirmed working on Xray Cloud** — "There are no steps defined" seen in last test. May need different format or Xray Cloud v2 API. Steps currently appear only in description as fallback.
- **Tests linking to Test Set:** `add_tests_to_set` tries Xray Server API then Jira issue links with "Tests"/"is member of"/"Relates" types. **Xray Cloud internal relationship (the tab in Test Set)** requires Xray's own data model — standard issue links may not appear in the Tests tab. APR-43 Test Set was empty in last test.
- **CSV Test Set column:** works when user types the Test Set key in the input field, or if populated automatically after Push All. Manual entry required if test set was pre-created.

### Not yet built ❌
- Preconditions as proper Xray Precondition issues (they go to description for now)
- Test Set ↔ Tests tab linking via Xray Cloud API v2 (requires separate Xray API key/token)
- Regression Pack (sprint-level cross-story TC subset)

---

## 8. Xray Cloud API — what we know

The user's Jira is **ilyaskadri.atlassian.net** (Jira Cloud) with **Xray for Jira Cloud** installed.

| What we want | API endpoint tried | Status |
|---|---|---|
| Create Test issue | `POST /rest/api/3/issue` with `issuetype: "Test"` | ✅ Works |
| Create Test Set | `POST /rest/api/3/issue` with `issuetype: "Test Set"` | ✅ Works |
| Push test steps | `POST /rest/raven/1.0/api/test/{key}/step` | ⚠️ Returns non-success or silent fail |
| Link tests to Test Set | `POST /rest/raven/1.0/api/testset/{key}/test` | ⚠️ Silent fail for Cloud |
| Link via Jira | `POST /rest/api/3/issueLink` with type "Tests" | ⚠️ Creates a link but may not appear in Tests tab |

**Root cause of steps/linking issue:** Xray Cloud's Test Sets and Test Steps use an internal data model separate from standard Jira issue links. The REST API v1 at the Jira base URL works for Xray Server/DC but has limited support on Cloud. Xray Cloud v2 API (`https://xray.cloud.getxray.app/api/v2/`) requires a **separate Xray API key** (not the regular Jira API token).

**Next thread should investigate:**
1. Can the user generate an Xray Cloud API key from their Xray settings?
2. If yes, add Xray API key storage to the profile and use the v2 endpoints for steps + test set linking
3. If no, use CSV import as the primary workflow (already working with Test Set column)

---

## 9. Known problems

See `DEFECTS.md` for full register. Current open items:

| ID | Issue | Status |
|---|---|---|
| VRD-D013 | README out of date | Open (Low priority) |
| VRD-D015 | Xray test steps not in Test Details tab | Open — partial fix in place |
| VRD-D016 | Tests not auto-linked inside Test Set | Open — partial fix in place |

---

## 10. Roadmap / next steps (priority order)

1. **Xray Cloud API v2** — investigate Xray API key to fix steps + Test Set linking (§8)
2. **Milestone 2 deploy** — Railway Hobby plan (~$5/month), then `git push` to Railway
3. **S6-2 landing page** — complete marketing content at `/landing`
4. **Sprint 4 — Licensing** — on-prem licence key system
5. **Sprint 7 — Regression Pack** — sprint-level TC picker → push as Regression Test Set

---

## 11. Hard constraints (do not violate)

- **Python stack only.** No external services beyond the user's own Jira/Anthropic.
- **Never commit secrets** (Anthropic key, Jira tokens) to the repo or commit messages.
- **EVOLVE, NEVER BREAK:** small, incremental, behaviour-preserving steps only. Freeze before risky work. Smoke test (48 tests) green before AND after every change.
- **Freeze first:** always create `snapshot/vX.Y.Z-description` branch before starting new feature work.
- SQLite locally / PostgreSQL on Railway — same code, no fork.

---

## 12. Do-not-re-ask glossary

- **Which branch?** `claude/confident-maxwell-nJkvm` — always verify with `git branch`
- **How to start?** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Browser URL?** `http://127.0.0.1:8000` (NOT `0.0.0.0:8000` — that doesn't work in a browser)
- **Git checkout fails?** Run `git reset --hard HEAD` first, then checkout
- **OneDrive locks files?** Common symptom: "deletion of directory failed" — type `n` and continue
- **Which page has new features?** `/generate/{issue_key}` — reached via Generate nav → Projects → pick story → Generate
- **What does the Generate nav link point to?** `/projects` (fixed in this session — it was `/` before)
- **Does / show old page when logged in?** No — it redirects to `/dashboard` now (fixed this session)
- **Are users persisted?** Yes — Sprint 3, DB-backed, `user_repository.py`
- **Model id?** `claude-sonnet-4-6`
- **Xray installed?** Yes — confirmed. APR-43 (Test Set) and APR-47 (Test) created this session.
- **Test steps in Xray?** Currently only in description — Xray Cloud step API not confirmed working yet (see §8)
- **Jira base URL?** ilyaskadri.atlassian.net
