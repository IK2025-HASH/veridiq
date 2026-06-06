# Verid-iq — Project Handoff / Working Context

> **Read this first.** This file is the single source of truth for picking up
> work on Verid-iq in a fresh session. It reflects the *actual current state*
> of the code — `README.md` is partly aspirational and does NOT describe what
> runs today. When in doubt, trust this file and the code over the README.

Last updated: 2026-06-06 · Active branch: `claude/confident-maxwell-nJkvm` · Latest release: **v1.1.0** (Xray Cloud v2 GraphQL)

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
- **v1.1.0 (✅ complete — 2026-06-06):** Xray Cloud v2 GraphQL integration. Test steps appear in Test Details tab. Each precondition becomes a separate Xray Pre-Condition issue. Tests auto-link inside Test Set. Preconditions editable inline before push. Issue naming prefixes (TC-N, PC-N, TS:, NTC-N, BDD-N, EC-N). Rate limit fix. AI model fix.
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
| Xray installed | ✅ Yes — Xray Cloud v2 GraphQL confirmed working (steps, preconditions, test sets) |
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
  - `snapshot/v1.1.0-xray-graphql` — v1.1.0 major release: Xray Cloud v2 GraphQL (steps + preconditions + test sets)
- Roll back: `git fetch origin <branch> && git reset --hard origin/<branch>`
- Tags don't work on this remote (HTTP 403) — use branches instead

**To create a new freeze before risky work:**
```powershell
git checkout -b snapshot/vX.Y.Z-description
git push -u origin snapshot/vX.Y.Z-description
git checkout claude/confident-maxwell-nJkvm
```

---

## 7. Current feature state (v1.1.0 as of 2026-06-06)

### Working ✅
- **Generate flow:** Projects → Stories → Generate page (`/generate/{issue_key}`)
- **Nav:** "Generate" link → `/projects`; `/` for logged-in users → redirects to `/dashboard`
- **Test Set button:** generates test cases; auto-checks "Group into Test Set" checkbox
- **Inline card edit:** Edit/Save/Cancel on each TC card; re-parses content after save
- **Download formats:** Text (plain), CSV (with Test Set column + manual key input), JSON
- **Push individual card:** Push button per card → creates Xray Test issue + links to story
- **Push All with Test Set:** creates Test Set issue first → pushes all TCs → links them (Tests tab populated via GraphQL)
- **Test steps in Xray Test Details:** each step pushed via `addTestStep` GraphQL mutation — confirmed appearing in Xray Test Details tab ✅
- **Preconditions as separate Xray issues:** each precondition → one `createPrecondition` GraphQL call → separate Pre-Condition issue in Xray Preconditions tab ✅
- **Tests linked inside Test Set:** `addTestsToTestSet` GraphQL mutation — Tests tab populated ✅
- **Preconditions editable inline:** each precondition shown as an editable text input before push; changes reflected in pushed content ✅
- **Issue naming prefixes:** TC-N (test cases), PC-N (preconditions), TS: (test sets), NTC-N (negative), BDD-N (BDD), EC-N (exploratory) ✅
- **Backlog Story filter:** Projects → Stories page shows only `issuetype = Story` items ✅
- **Rate limit fix:** per-user rate limiting (slowapi callable) — authenticated users no longer hit the IP rate limit incorrectly ✅

### Not yet built ❌
- Regression Pack (sprint-level cross-story TC subset)
- Test Execution push (create Test Execution from Test issue)
- Bulk backlog generation (multi-story batch)

---

## 8. Xray Cloud API — confirmed facts (v1.1.0)

The user's Jira is **ilyaskadri.atlassian.net** (Jira Cloud) with **Xray for Jira Cloud** installed.

**Auth:** `POST https://xray.cloud.getxray.app/api/v2/authenticate` with `{"client_id": ..., "client_secret": ...}` → returns a Bearer JWT string (stored in admin settings, Fernet-encrypted).

**Key fact: REST endpoints return 404 on this Cloud plan. Use GraphQL only.**

| What we want | Working approach | Endpoint |
|---|---|---|
| Create Test issue | Jira REST API | `POST /rest/api/3/issue` with `issuetype: "Test"` ✅ |
| Create Test Set | Jira REST API | `POST /rest/api/3/issue` with `issuetype: "Test Set"` ✅ |
| Push test steps | GraphQL `addTestStep` (one call per step) | `POST https://xray.cloud.getxray.app/api/v2/graphql` ✅ |
| Create Precondition issue | GraphQL `createPrecondition` | `POST https://xray.cloud.getxray.app/api/v2/graphql` ✅ |
| Link preconditions to test | GraphQL `addPreconditionsToTest` | `POST https://xray.cloud.getxray.app/api/v2/graphql` ✅ |
| Link tests to Test Set | GraphQL `addTestsToTestSet` | `POST https://xray.cloud.getxray.app/api/v2/graphql` ✅ |
| Push test steps (REST) | `PUT /api/v2/test/{id}/steps` | ❌ 404 on this Cloud plan |
| Link tests (REST) | `POST /api/v2/testset/{id}/test` | ❌ 404 on this Cloud plan |

**Important GraphQL mutation names** (others will error):
- Steps: `addTestStep(issueId: String!, step: CreateStepInput!)` — call once per step, NOT `updateTestSteps`
- Preconditions: `createPrecondition(...)` then `addPreconditionsToTest(...)`
- Test Sets: `addTestsToTestSet(issueId: String!, testIssueIds: [String!]!)`

**`issueId` parameter** = Jira numeric ID from `data["id"]` in issue creation response (e.g. `"12345"`), NOT the key (e.g. `APR-80`).

**Pre-Condition issue type** in Jira project not required — `createPrecondition` GraphQL bypasses Jira issue type scheme entirely.

---

## 9. Known problems

See `DEFECTS.md` for full register. Current open items:

| ID | Issue | Status |
|---|---|---|
| VRD-D013 | README out of date | Open (Low priority) |
| VRD-D015 | Xray test steps not in Test Details tab | **Verified ✅ — fixed v1.1.0 (GraphQL `addTestStep`)** |
| VRD-D016 | Tests not auto-linked inside Test Set | **Verified ✅ — fixed v1.1.0 (GraphQL `addTestsToTestSet`)** |

---

## 10. Roadmap / next steps (priority order)

1. **Milestone 2 deploy** — Railway Hobby plan (~$5/month), then `git push` to Railway
2. **S6-2 landing page** — complete marketing content at `/landing`
3. **Sprint 4 — Licensing** — on-prem licence key system
4. **S7-1 Xray test repository view** — `/projects/{key}/tests` listing
5. **S7-2 Push to Test Execution** — create Test Execution from pushed test
6. **Sprint 7 — Regression Pack** — sprint-level TC picker → push as Regression Test Set

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
- **Test steps in Xray?** ✅ Yes — working via GraphQL `addTestStep` mutation (v1.1.0)
- **Preconditions in Xray?** ✅ Yes — each precondition is a separate Xray Pre-Condition issue via `createPrecondition` GraphQL
- **Tests in Test Set?** ✅ Yes — via `addTestsToTestSet` GraphQL — Tests tab populated after Push All
- **Xray REST API?** ❌ Returns 404 on this Cloud plan — GraphQL only (see §8)
- **Jira base URL?** ilyaskadri.atlassian.net
