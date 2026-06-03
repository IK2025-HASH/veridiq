# Defect Register — Verid-iq

The canonical log of defects found in Verid-iq. We dogfood our own discipline:
every defect gets an ID, severity, status, root cause, and resolution, and is tied
to the commit/freeze that fixed it.

## Conventions
**ID:** `VRD-Dnnn` (sequential).
**Severity** (impact): `S1 Critical` (app unusable / data loss) · `S2 High` (major
feature broken, no workaround) · `S3 Medium` (feature broken, workaround exists) ·
`S4 Low` (cosmetic / docs).
**Priority** (urgency): `P1`…`P4`.
**Status:** `Open` → `In Progress` → `Fixed` → `Verified` → `Closed`; or `Deferred`
/ `Won't Fix`. ("Verified" = covered by an automated test or confirmed by the owner.)
**Found by:** how it surfaced (smoke test, manual, owner report, code review).

---

## Summary
| ID | Summary | Sev | Pri | Module | Status | Fixed in |
|----|---------|-----|-----|--------|--------|----------|
| VRD-D011 | "Push to Xray" fails ("Xray does not connect") | S2 | P1 | product/xray | **Open** | — |
| VRD-D012 | Non-admin users not persisted across restart | S3 | P3 | platform/users | **Deferred** (M2) | — |
| VRD-D013 | README out of date vs actual product reality | S4 | P4 | docs | **Open** | — |
| VRD-D008 | `/team` returns 500 — template missing | S2 | P1 | platform/users | Verified | `8d4c1bc` (0.3.0) |
| VRD-D009 | `/invoices` returns 500 — template missing | S2 | P1 | platform/billing | Verified | `8d4c1bc` (0.3.0) |
| VRD-D003 | 500 on setup/login — passlib×bcrypt crash | S1 | P1 | platform/auth | Verified | `44f1d91` (0.1.0) |
| VRD-D001 | AI generation 404 — invalid model id | S1 | P1 | product/generation | Verified | `249bfe3` (0.1.0) |
| VRD-D002 | Jira credentials lost on every restart | S2 | P1 | product/jira | Verified | `249bfe3` (0.1.0) |
| VRD-D005 | Jira issue list 410 Gone — deprecated endpoint | S2 | P2 | product/jira | Verified | `4cee3c3` (0.1.0) |
| VRD-D007 | Fresh install crashes — email-validator missing | S2 | P2 | platform | Verified | `04da5c2` (0.1.0) |
| VRD-D004 | `create_session()` called with wrong arg count | S2 | P1 | platform/auth | Verified | `44f1d91` (0.1.0) |
| VRD-D006 | `datetime('now')` not Postgres-compatible | S3 | P2 | platform/settings | Verified | `fa40614` (pre-0.1.0) |
| VRD-D010 | Generate page had no navigation | S3 | P3 | product/web | Verified | `04da5c2` (0.1.0) |

---

## Open / active defects

### VRD-D011 — "Push to Xray" fails ("Xray does not connect")
- **Severity:** S2 High · **Priority:** P1 · **Status:** Open
- **Module:** `product/integrations/xray` (currently in `app/core/jira_client.py` + `app/api/jira.py`)
- **Found by:** Owner report (manual)
- **Description:** Clicking *Approve & Push to Xray* on a generated artifact fails;
  the owner reported "Xray does not connect."
- **Steps to reproduce:** Connect Jira → generate test cases for a story → click
  *Approve & Push to Xray*.
- **Expected:** A Test issue is created in the project and linked to the source story
  (one key per pushed item).
- **Actual:** Push fails (exact error text not yet captured).
- **Analysis / context:** The previous MVP "StoryToTest" pushed test cases to the
  **same** Jira and they became real issues (APR-30/31/32) — see HANDOFF §3b. So the
  Jira/Xray side works; this is a **Verid-iq implementation gap** (likely issue-type
  name, ADF payload shape, or the single-blob-vs-per-card approach), NOT a missing
  "Test" type or a Jira limitation.
- **Next step:** Capture the literal red `✗ …` message; compare our `create_xray_test`
  payload to the per-card create that worked in StoryToTest. Likely fixed together
  with Tier 3 (per-test-case cards, each pushed individually).
- **Blocked on:** the exact error string from the owner.

### VRD-D012 — Non-admin users not persisted across restart
- **Severity:** S3 Medium · **Priority:** P3 · **Status:** Deferred (Milestone 2)
- **Module:** `platform/users`
- **Found by:** Code review
- **Description:** In Milestone 1, only the admin is persisted (settings table) and
  restored on startup. Other registered users live in the in-memory `USERS` dict and
  vanish on restart.
- **Workaround:** Single-admin local use is unaffected.
- **Resolution plan:** Make users DB-backed when `platform/users` is built (Milestone 2 /
  user-management module). Tracked in HANDOFF §4 and `app/platform/users/README.md`.

### VRD-D013 — README out of date vs actual product
- **Severity:** S4 Low · **Priority:** P4 · **Status:** Open
- **Module:** docs
- **Description:** `README.md` describes an aspirational state (Postgres-only,
  marketplace, Atlassian Connect) that doesn't match the Milestone-1 reality. A banner
  now points readers to HANDOFF/ARCHITECTURE, but the body still needs a rewrite.
- **Resolution plan:** Rewrite README once the modular migration stabilises.

---

## Closed defects (history)

### VRD-D008 — `/team` returns 500 (template missing) — Verified
- **Sev:** S2 · **Module:** platform/users · **Found by:** **Smoke test** (`test_smoke.py`)
- **Description:** `/team` is linked in the global nav but `web/team.html` did not
  exist → `TemplateNotFound` → HTTP 500 for any logged-in user clicking *Team*.
- **Root cause:** Route + nav link shipped without the template.
- **Resolution:** Added `web/team.html`; covered by `test_core_pages_render[/team]`.
- **Fixed in:** `8d4c1bc` (0.3.0).

### VRD-D009 — `/invoices` returns 500 (template missing) — Verified
- **Sev:** S2 · **Module:** platform/billing · **Found by:** **Smoke test**
- **Description:** As D008, for `/invoices` (`web/invoices.html` missing).
- **Resolution:** Added `web/invoices.html`; covered by smoke test.
- **Fixed in:** `8d4c1bc` (0.3.0).

### VRD-D003 — 500 on setup/login (passlib × bcrypt) — Verified
- **Sev:** S1 · **Module:** platform/auth · **Found by:** Running the server (manual)
- **Root cause:** `passlib==1.7.4` self-test crashes with `bcrypt>=4.1` (raises on
  >72-byte passwords). Every `hash_password()` failed → 500 on all auth flows.
- **Resolution:** Replaced passlib with direct `bcrypt`. **Fixed in:** `44f1d91` (0.1.0).

### VRD-D001 — AI generation 404 (invalid model id) — Verified
- **Sev:** S1 · **Module:** product/generation · **Found by:** Owner report
- **Root cause:** Model id `claude-sonnet-4-20250514` does not exist → Anthropic 404.
- **Resolution:** Set model to `claude-sonnet-4-6`. **Fixed in:** `249bfe3` (0.1.0).

### VRD-D002 — Jira credentials lost on every restart — Verified
- **Sev:** S2 · **Module:** product/jira · **Found by:** Owner report
- **Root cause:** Credentials stored only in the in-memory `USERS` dict.
- **Resolution:** Persist to DB (encrypted token) on connect; restore on startup.
  **Fixed in:** `249bfe3` (0.1.0).

### VRD-D005 — Jira issue list 410 Gone — Verified
- **Sev:** S2 · **Module:** product/jira · **Found by:** Owner report (screenshot)
- **Root cause:** Atlassian deprecated `/rest/api/3/search` (returns 410).
- **Resolution:** Switched to `/rest/api/3/search/jql`. **Fixed in:** `4cee3c3` (0.1.0).

### VRD-D007 — Fresh install crashes (email-validator missing) — Verified
- **Sev:** S2 · **Module:** platform · **Found by:** Code review while testing
- **Root cause:** `EmailStr` needs `email-validator`, not pulled by `pydantic==2.7.1`.
- **Resolution:** `pydantic[email]==2.7.1`. **Fixed in:** `04da5c2` (0.1.0).

### VRD-D004 — `create_session()` wrong arg count — Verified
- **Sev:** S2 · **Module:** platform/auth · **Found by:** Running the server
- **Root cause:** Called with 2 args; signature needs 3 (`user_agent`).
- **Resolution:** Pass `user_agent`. **Fixed in:** `44f1d91` (0.1.0).

### VRD-D006 — `datetime('now')` not Postgres-compatible — Verified
- **Sev:** S3 · **Module:** platform/settings · **Found by:** Code review
- **Root cause:** SQLite-only function in settings SQL; would fail on Railway Postgres.
- **Resolution:** Use `CURRENT_TIMESTAMP`. **Fixed in:** `fa40614` (pre-0.1.0).

### VRD-D010 — Generate page had no navigation — Verified
- **Sev:** S3 · **Module:** product/web · **Found by:** Owner report
- **Root cause:** `index.html` is standalone (doesn't extend `_base.html`) and shipped
  without nav links → no way to reach other pages from `/`.
- **Resolution:** Added the full nav to the Generate header. **Fixed in:** `04da5c2` (0.1.0).

---

## Process notes
- New defects: add a row to **Summary** + a detail entry; reference the fixing commit.
- A fix should land with a test where practical, so the defect moves to **Verified**
  and can't silently regress. The smoke test is the first line of that defence.
