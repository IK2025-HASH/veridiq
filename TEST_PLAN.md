# Test Plan & Coverage — Verid-iq

What is tested, where, and how to see it. Companion to `DEFECTS.md`.

## How to SEE what's tested (3 ways)
1. **List every test by name** (most useful):
   ```
   pytest tests/ -v
   ```
   Each line is one test case, e.g. `tests/test_smoke.py::test_core_pages_render[/projects] PASSED`.
2. **Just the count / pass-fail:** `pytest tests/ -q`  → e.g. `48 passed in 1.4s`.
3. **Read the source:** the test files below are the executable spec.

> If you see `15 passed` you are on an OLD checkout — `git pull` to get the smoke
> test (then it's **48**).

## Test-run evidence (reports)
Screenshots are not test evidence. Generate proper, reproducible reports instead:
- **One click:** double-click **`test-evidence.bat`** (run from the activated venv).
- **Or by command:**
  ```
  pytest tests/ -v --junitxml=reports/junit.xml --html=reports/report.html --self-contained-html
  ```
This writes:
- `reports/report.html` — readable page: every test, pass/fail, timing, failure detail.
- `reports/junit.xml` — standard CI/audit format.

`reports/` is **gitignored** — regenerate any time; nothing is committed. Requires
`pytest-html` (in `requirements.txt`).

## Where the tests live
| File | What it covers |
|---|---|
| `tests/test_smoke.py` | End-to-end safety net (boots app, renders pages, invariants) |
| `tests/test_veridiq.py` | Unit tests (knowledge store, prompt assembly, API validation) |
| `tests/test_playwright.py` | Browser tests: 7 Playwright tests with live uvicorn fixture |
| `tests/conftest.py` | Shared setup: hermetic SQLite DB, fixtures (not tests) |

---

## How to run Playwright tests
```
playwright install chromium          # one-time setup
pytest tests/test_playwright.py --browser chromium -v
```
Screenshots land in `screenshots/` (gitignored). In CI (GitHub Actions), they are
uploaded as the `playwright-screenshots` artifact under the **Playwright Screenshots** job.

---

## Coverage map

### A. Smoke / end-to-end — `tests/test_smoke.py`
| Test | Asserts |
|---|---|
| `test_app_boots` | App starts (lifespan runs); `/api/health` returns ok |
| `test_core_pages_render[…]` ×15 | Each core page renders **200, no 5xx**: `/landing`, `/terms`, `/privacy`, `/dashboard`, `/projects`, `/projects/APR/stories`, `/generate/APR-28`, `/credits`, `/profile`, `/team`, `/invoices`, `/security`, `/admin`, `/admin/settings`, `/admin/users` |
| `test_core_apis_ok[…]` ×4 | `/api/health`, `/api/generation-types`, `/api/jira/status`, `/api/credits/balance` return 200 |
| `test_no_route_5xx[…]` ×9 | Jira/auth/setup GET routes + `/` (now redirects 302 for logged-in users) never 5xx (controlled 4xx/302 is fine) |
| `test_generate_input_validation` | `/api/generate` rejects bad input with 422 (no crash) |
| `test_expected_routes_registered` | Core routes still exist (catches accidental removal) |
| `test_scaffold_packages_import` | `platform/`, `product/`, `delivery/` packages import |
| `test_platform_does_not_depend_on_product_or_delivery` | Architecture rule: `platform/` never imports `product/`/`delivery/` |

### B. Unit — `tests/test_veridiq.py`
| Area | Tests |
|---|---|
| Knowledge store | loads volumes · returns chunks · empty dir returns "" |
| Prompt assembly | returns (system,user) tuple · works for all 8 generation types · injects Jira issue context · batch-types set is correct |
| API endpoints | `/api/health` · `/api/generation-types` (8 types) · `/` serves · `/terms` · `/privacy` |
| Input validation | generate rejects short input / invalid type / out-of-range quantity (422) |

---

### C. Browser / Playwright — `tests/test_playwright.py`
| Test | Asserts |
|---|---|
| `test_landing_page` | `/landing` renders; screenshot saved |
| `test_login_page` | Email + password inputs visible; screenshot saved |
| `test_register_page` | `/register` renders; screenshot saved |
| `test_homepage_desktop` | `/` renders at desktop viewport; screenshot saved |
| `test_homepage_mobile` | `/` at 375px — `#nav-hamburger` visible; screenshot saved |
| `test_hamburger_opens_menu` | Click hamburger → `#mobile-menu` visible; screenshot saved |
| `test_terms_page` | `/terms` renders; screenshot saved |

Run separately (requires `playwright install chromium`). CI uploads screenshots as an artifact.

---

## What is NOT yet covered (gaps / TODO)
- **AI generation output** — not asserted (would call the real Anthropic API). The
  engine is exercised only up to prompt assembly.
- **Xray push (mock-Jira)** — VRD-D011 fixed; a mock-Jira pytest case would add
  auto-regression protection for individual test case push and Test Set creation.
- **Xray step API (VRD-D015)** — `_push_xray_steps` not unit-tested with a mock HTTP
  client. Should be added alongside the Xray Cloud v2 API implementation (S7-0).
- **Test Set linking (VRD-D016)** — `add_tests_to_set` not unit-tested. Add alongside
  S7-0 with mock Xray Cloud v2 responses.
- **Auth flows** — register/login/2FA happy-paths beyond setup are not asserted.
- **Token/id routes** — `/invoices/{id}`, `/auth/reset-password/{token}`, `/join/{token}`
  need fixtures; excluded from smoke for now.
- **Playwright: authenticated pages** — current browser tests cover only public pages.
  Add login flow + generate page + admin page in next Playwright iteration.
- **Download format output** — Text/CSV/JSON download logic in `generate_issue.html` is
  client-side JS; not covered by pytest. Browser-level Playwright test needed.
- **Inline card edit** — JS-only; not covered. Playwright test needed.

New fixes should add a test here so the defect moves to **Verified** in `DEFECTS.md`.
