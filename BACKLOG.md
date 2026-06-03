# Verid-iq — Product Backlog & Sprint Plan

> **Agile framing (AI-paced):**
> - A **sprint** is a logical batch of related work, not a calendar time-box.
>   Each sprint ends when: code works, CI is green, freeze branch is pushed,
>   and the owner has reviewed + pulled.
> - **Definition of Done (every story):** code merged, pytest green (local),
>   GitHub Actions CI green, smoke test passes, freeze branch created if
>   it's a sprint boundary.
> - **CI/CD discipline:** every sprint adds automated tests for what it builds.
>   Testing is not a separate sprint — it is part of every story's done criteria.
> - Sprints are ordered by dependency and commercial priority. Re-order at any
>   sprint boundary if priorities shift.

---

## Backlog at a glance

| Sprint | Theme | Key deliverable |
|--------|-------|-----------------|
| ~~S0~~ | ~~Core product~~ | ~~v0.4.0 — per-item Xray push, 48 tests~~ ✅ |
| **S1** | CI/CD + Test foundation | GitHub Actions pipeline; Playwright skeleton |
| **S2** | Deploy | Railway + PostgreSQL; app live on a URL |
| **S3** | Users & Auth | DB-backed multi-user; roles; 2FA; password reset |
| **S4** | Licensing | On-prem licence key; seat limits; editions |
| **S5** | Knowledge Management | Upload volumes; knowledge-augmented generation |
| **S6** | UX / UI Polish | Tier 3 TC cards; landing page; mobile pass |
| **S7** | Deeper Xray | Test execution push; bulk backlog generation |
| **S8** | Marketplace | Atlassian Connect; OAuth; listings |
| **S9** | Billing | Stripe/credits; invoices; top-up flow |
| **S10** | Modular migration | Move code into platform/product/delivery — step by step |

---

## Sprint 0 — Core product ✅ DONE (v0.4.0)

Everything working at the freeze `snapshot/v0.4.0-per-item-xray`.

- ✅ 8 generation types (SSE streaming)
- ✅ Jira connect / project browser / per-story generate
- ✅ Per-item Xray push (each TC → its own Jira issue, linked back)
- ✅ 48 pytest smoke + unit tests
- ✅ Hermetic test environment (SQLite, fake keys, session-scoped fixtures)
- ✅ Reproducible test evidence (`test-evidence.bat`, pytest-html)
- ✅ Additive modular scaffold (`platform/`, `product/`, `delivery/`)

---

## Sprint 1 — CI/CD + Test Foundation

**Goal:** every push to GitHub automatically runs all tests and tells you
pass/fail without you touching the terminal. Playwright added for browser-level
tests and screenshot evidence.

### Stories

#### S1-1 — GitHub Actions CI pipeline
- Trigger: every push + every PR to `main` or `claude/*`
- Steps: checkout → install Python deps → run `pytest tests/ -v` → upload
  `reports/` as a downloadable build artifact
- Status badge on README so you can see CI health at a glance
- **Tests added:** CI itself is the test (if it goes red, you know immediately)

#### S1-2 — Playwright skeleton + screenshot evidence
- Install `playwright` + `pytest-playwright` (headless Chromium)
- Start a live test server (`uvicorn`) in a pytest fixture
- First 3 browser tests: homepage renders, login flow works, generate page loads
- Screenshots captured on failure and on pass; attached to pytest-html report
- **This closes the "I expected real screenshots" request**

#### S1-3 — Lint & format gate in CI
- Add `ruff` (fast Python linter) to CI step
- Fail the pipeline if there are lint errors
- One-command local fix: `ruff check . --fix`

#### S1-4 — Branch protection rule
- Protect `main`: require CI green before merge
- All development stays on feature/sprint branches; only green code reaches `main`

#### S1-5 — README rewrite (VRD-D013)
- Replace aspirational README with accurate Milestone-1 description
- Sections: what it is, how to run locally, how to run tests, CI badge, licence

**Sprint 1 freeze branch:** `snapshot/v1.1.0-ci-foundation`

---

## Sprint 2 — Deploy (Milestone 2)

**Goal:** app running on a public URL (Railway + PostgreSQL). Anyone you send
the link to can use it — no local setup needed.

### Stories

#### S2-1 — PostgreSQL compatibility audit
- Run full test suite against a local Postgres (via Docker or Railway dev env)
- Fix any SQLite-isms that surface (e.g. column types, JSON fields)
- CI matrix: test against both SQLite and Postgres

#### S2-2 — Railway deployment config
- `Procfile` / `railway.toml` for uvicorn
- `DATABASE_URL` injected as Railway env var (no code change needed — already
  read from environment in `config.py`)
- Health check endpoint (`/api/health`) wired to Railway health monitor

#### S2-3 — Alembic migrations
- Replace `create_all()` (dev shortcut) with proper Alembic migrations
- CI runs migrations before tests on the Postgres matrix
- Migration history tracked in `alembic/versions/`

#### S2-4 — Secrets management for production
- All secrets (Anthropic key, secret key) set as Railway env vars
- No secrets in code or `.env` files committed to repo
- Document the required env vars in a `.env.example` (values redacted)

#### S2-5 — Smoke test against live deploy
- Post-deploy step in CI: hit `/api/health` on the Railway URL
- If health check fails, deployment is marked failed

**Sprint 2 freeze branch:** `snapshot/v1.2.0-railway-deploy`

---

## Sprint 3 — Users & Auth

**Goal:** real multi-user product. Users persist across restarts. Roles enforced.

### Stories

#### S3-1 — DB-backed user model
- Replace in-memory `USERS` dict with a proper `users` table
- Closes VRD-D012 (non-admin users lost on restart)
- Migration: existing admin row carried forward

#### S3-2 — Registration flow
- `/auth/register` — email + password + invite token
- Admin can generate invite links from `/admin/users`
- Email verification (token sent via SMTP if configured, skipped if not)

#### S3-3 — Roles
- Three roles: `admin`, `qa_lead`, `tester`
- Role-based route guards (decorator / dependency)
- Admin UI shows role column; admin can promote/demote

#### S3-4 — Password reset
- `/auth/forgot-password` → email with reset token
- `/auth/reset-password/{token}` → new password form
- Token expires in 1 hour; single-use

#### S3-5 — 2FA (TOTP)
- `/security` page — enable/disable 2FA
- QR code generated with `pyotp`
- Login flow: if 2FA enabled, prompt for code after password
- Backup codes (10 single-use codes) generated and shown once

#### S3-6 — Auth tests
- pytest: register → login → access protected route → logout
- Playwright: full login flow with screenshot
- pytest: 2FA happy path + wrong code rejects

**Sprint 3 freeze branch:** `snapshot/v1.3.0-user-management`

---

## Sprint 4 — Licensing

**Goal:** on-prem licence key system. A customer buys a key, installs the app,
pastes the key — access is gated without any phone-home.

### Stories

#### S4-1 — Licence key format & generation
- Key format: `VRD-{edition}-{seats}-{expiry}-{signature}` (Base58 + HMAC)
- Generator script (runs offline, owned by Network Logic): `tools/generate_licence.py`
- Output: human-typeable key, ~40 chars

#### S4-2 — Offline validation
- `platform/licensing/validator.py` — validates signature locally (no HTTP call)
- Checks: valid signature, expiry date, edition, seat count
- Result: `LicenceState(valid, edition, seats_allowed, expires_at, grace_until)`

#### S4-3 — Editions & feature gating
- Three editions: `community` (free, limited), `professional`, `enterprise`
- Feature flags per edition stored in `platform/licensing/editions.py`
- Decorator `@require_edition("professional")` on routes that need it

#### S4-4 — Seat enforcement
- Seat = one active registered user
- On login: check active user count ≤ licence seats
- Admin UI shows seats used / seats allowed

#### S4-5 — Grace period & expiry UI
- 14-day grace period after expiry (app still works, banner shown)
- After grace: read-only mode (can view, cannot generate or push)
- Admin `/admin/settings` shows licence status, expiry, edition

#### S4-6 — Licence tests
- pytest: valid key → access granted
- pytest: expired key → grace mode
- pytest: expired + past grace → read-only
- pytest: wrong signature → rejected
- pytest: seat limit hit → 11th login blocked

**Sprint 4 freeze branch:** `snapshot/v1.4.0-licensing`

---

## Sprint 5 — Knowledge Management

**Goal:** users can upload their own test standards, templates, or guidelines.
The AI uses them when generating, producing output tailored to their context.

### Stories

#### S5-1 — Knowledge volume storage
- `/admin/knowledge` — upload PDF / Markdown / plain text files
- Stored in `knowledge/volumes/{name}/` (gitignored content)
- Metadata in DB: name, type, size, uploaded_by, created_at

#### S5-2 — Knowledge retrieval
- `platform/knowledge/store.py` — load and chunk volumes at startup
- Simple keyword / BM25 retrieval (no vector DB needed initially)
- Returns top-N relevant chunks for a given generation request

#### S5-3 — Knowledge-augmented prompts
- Inject retrieved chunks into the system prompt
- Per-generation-type selection: which volumes are relevant
- Admin can tag volumes by generation type

#### S5-4 — Knowledge UI
- `/admin/knowledge` — list volumes, upload, delete
- Tester can see which volumes are active (read-only view)
- Show which knowledge was used in a generation (small info panel)

#### S5-5 — Knowledge tests
- pytest: upload → retrieves relevant chunks
- pytest: empty dir → generates without error
- Playwright: upload flow, volume visible in list

**Sprint 5 freeze branch:** `snapshot/v1.5.0-knowledge-mgmt`

---

## Sprint 6 — UX / UI Polish

**Goal:** the app looks and feels like a real commercial product. Ready for
marketplace screenshots and demo videos.

### Stories

#### S6-1 — Tier 3 TC cards (structured output)
- Parse AI output into rich cards: type tag (Positive/Negative/Edge),
  priority badge, Preconditions, numbered Steps table (Action + Expected),
  Expected Outcome
- Matches the StoryToTest UX target (§3b of HANDOFF) — inspiration not copy
- Existing per-item push buttons carry forward

#### S6-2 — Landing / marketing page
- Public-facing page at `/landing` (no login required)
- Hero: "Turn Jira Stories into Test Cases. Instantly."
- Feature highlights, CTA to sign up or connect Jira
- Network Logic branding

#### S6-3 — Mobile / responsive pass
- All pages usable on a phone (the user reviewed on mobile today)
- Minimum: nav collapses, cards stack, buttons are tappable

#### S6-4 — Playwright screenshot suite
- Screenshot test for every core page: `/`, `/projects`, `/projects/{k}/stories`,
  `/generate/{key}`, `/admin`
- Screenshots attached to pytest-html report (this closes the original request)
- CI uploads the screenshot folder as a build artifact

#### S6-5 — Empty states & loading polish
- Consistent empty states across all list pages
- Loading skeletons instead of spinners on slow Jira calls
- Error states show actionable messages (not raw codes)

**Sprint 6 freeze branch:** `snapshot/v1.6.0-ux-polish`

---

## Sprint 7 — Deeper Xray & Jira

**Goal:** power features for QA teams who live in Xray daily.

### Stories

#### S7-1 — Xray test repository view
- `/projects/{key}/tests` — list existing Xray Test issues for the project
- Shows test key, summary, status, linked story
- Links back to Jira for full detail

#### S7-2 — Push to test execution
- After pushing a test, optionally create a Test Execution and add the test to it
- Useful for sprint-level test runs

#### S7-3 — Bulk backlog generation
- `/projects/{key}/bulk` — select multiple stories, choose type, generate all
- Progress bar per story; push all approved tests at once
- Rate-limited (1 story/sec to avoid Anthropic throttle)

#### S7-4 — Deeper Jira link
- Show story's acceptance criteria alongside description on generate page
- Pull `customfield_*` AC fields from Jira if configured

**Sprint 7 freeze branch:** `snapshot/v1.7.0-xray-power`

---

## Sprint 8 — Marketplace

**Goal:** app can be installed from Atlassian Marketplace by any Jira Cloud customer.

### Stories

#### S8-1 — Atlassian Connect descriptor
- `atlassian-connect.json` describing the app, scopes, webhook URLs
- Served at `/atlassian-connect.json`
- `delivery/atlassian_connect/` module (scaffold already exists)

#### S8-2 — OAuth 2.0 (3LO) install flow
- Jira Cloud calls our callback on install → we store the OAuth token
- Replace Basic-auth Jira client with OAuth token client for Cloud installs
- Basic auth kept for on-prem / Server customers

#### S8-3 — Multi-tenant isolation
- Per-installation data isolation (each Jira Cloud tenant gets their own context)
- Licence check per tenant

#### S8-4 — Marketplace listing content
- App description, screenshots (from S6-4), demo video link
- Privacy policy + terms of service pages (`/privacy`, `/terms` already exist)
- Pricing tiers matching licence editions

#### S8-5 — Security review
- OWASP Top 10 pass (automated: `bandit` + manual review)
- Dependency vulnerability scan (`pip-audit`)
- Added to CI pipeline

**Sprint 8 freeze branch:** `snapshot/v1.8.0-marketplace`

---

## Sprint 9 — Billing

**Goal:** real money in. Credits system, Stripe integration, invoices.

### Stories

#### S9-1 — Credits model
- Each generation call costs N credits (configurable per type)
- Credits purchased in bundles (100, 500, 1000)
- Low-credit warning banner

#### S9-2 — Stripe integration
- `/credits/buy` — Stripe Checkout session
- Webhook: `checkout.session.completed` → top up credits in DB
- Test mode in dev; live mode gated by env var

#### S9-3 — Real invoices
- Invoice generated on each credit purchase (PDF via `reportlab` or HTML → PDF)
- `/invoices` page shows real data (closes the current placeholder)
- Invoice download as PDF

#### S9-4 — Billing tests
- pytest: mock Stripe webhook → credits added
- pytest: zero credits → generation blocked with 402
- Playwright: buy flow (Stripe test card)

**Sprint 9 freeze branch:** `snapshot/v1.9.0-billing`

---

## Sprint 10 — Modular Migration

**Goal:** existing working code progressively moved into `platform/` / `product/` /
`delivery/`. No behaviour change — smoke test green throughout. Each step gets its
own freeze branch.

Each step is a separate mini-sprint:

| Step | What moves | Freeze |
|------|-----------|--------|
| 1 | `core/auth.py` → `platform/auth/` | `snapshot/v1.10.1-migrate-auth` |
| 2 | `core/settings_service.py` → `platform/settings/` | `snapshot/v1.10.2-migrate-settings` |
| 3 | `core/jira_client.py` → `product/integrations/jira/` | `snapshot/v1.10.3-migrate-jira` |
| 4 | `core/ai_engine.py` → `product/generation/` | `snapshot/v1.10.4-migrate-generation` |
| 5 | `api/web.py` routes → `delivery/webapp/` | `snapshot/v1.10.5-migrate-webapp` |

**Rule:** the smoke test (48+ tests) must be green before and after every step.
If it goes red, revert immediately — do not push.

---

## CI/CD pipeline (target state after Sprint 1)

```
Push to any branch
       │
       ▼
┌─────────────────────────────────────┐
│  GitHub Actions: CI                 │
│  1. Install Python deps             │
│  2. ruff lint check                 │
│  3. pytest (SQLite) -v              │
│  4. pytest (Postgres) -v  [S2+]     │
│  5. Playwright browser tests [S1+]  │
│  6. Upload reports/ as artifact     │
└──────────────┬──────────────────────┘
               │ green
               ▼
        PR to main?
               │ yes
               ▼
┌─────────────────────────────────────┐
│  GitHub Actions: Deploy             │
│  (after Sprint 2)                   │
│  1. Push to Railway                 │
│  2. Run Alembic migrations          │
│  3. Hit /api/health — must return ok│
└─────────────────────────────────────┘
```

---

## Definition of Done (per story)

- [ ] Code written and self-reviewed
- [ ] `pytest tests/ -q` green locally
- [ ] GitHub Actions CI green on the branch
- [ ] New behaviour covered by at least one automated test
- [ ] No new lint errors (`ruff check .`)
- [ ] No secrets committed
- [ ] DEFECTS.md updated if a defect is fixed
- [ ] CHANGELOG.md entry drafted (written at sprint close, not per story)

---

## Open defects carried into backlog

| ID | Description | Sprint |
|----|-------------|--------|
| VRD-D011 | Xray push error — likely resolved by per-item push; verify in S1 | S1 verify |
| VRD-D012 | Non-admin users not persisted across restart | S3 |
| VRD-D013 | README out of date | S1 |
