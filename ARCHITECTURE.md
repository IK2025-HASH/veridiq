# Verid-iq — Architecture & Folder Structure

Companion to `HANDOFF.md`. Captures (1) the product vision that drives
architecture, (2) the **current** folder structure, and (3) the **proposed
modular target** — a reusable platform skeleton separated from product-specific
code, so the scaffold can seed future Network Logic products.

> The target in §3 is a **proposal, not yet implemented**. It must be executed
> incrementally, each step behind a freeze branch with the smoke test passing.
> Do not bulk-move files without owner sign-off.

---

## 1. Product vision (drives every architectural decision)
Verid-iq is a **full commercial product**, not a personal tool or throwaway PoC.

**Launch surfaces (4):**
1. **LinkedIn** — owner's profile + a self-built LinkedIn community around it.
2. **Atlassian Marketplace** — Jira Cloud app (Test Management category).
3. **Xray Marketplace** — SmartBear / Xray ecosystem.
4. **Own landing page** — a subdomain of the Network Logic main domain.

**Architectural implications:**
- The same core must serve **multiple delivery surfaces**: a standalone web app
  (subdomain) AND an embedded Atlassian Connect app (Jira iframe panels). So
  business logic must NOT be coupled to the standalone web/HTML layer.
- Auth is multi-modal: email/password + LinkedIn OAuth today; Atlassian handles
  identity inside the Connect app. Auth must be pluggable.
- Billing/credits, users, teams, invoices, admin, settings, email — none of these
  are Verid-iq-specific. They are **platform capabilities** worth reusing across
  future products → they belong in a cleanly separable skeleton.
- "Reduce risk of breaking other things" → strong module boundaries, thin
  composition root, feature isolation, and a regression smoke test as a safety net.

---

## 2. CURRENT structure (as of 2026-06-03, commit 3918eff)
Layered monolith. ~3,500 lines Python, ~3,760 lines templates.

```
veridiq/
├── app/
│   ├── main.py                     # 161  composition root: lifespan, routers, middleware
│   ├── config.py                   #  48  env settings, DB url, model id
│   ├── database.py                 #  56  engine + create_tables (sync-in-thread)
│   │
│   ├── api/                        # ── HTTP route handlers ──
│   │   ├── auth.py                 # 445  register, login, LinkedIn OAuth, 2FA, sessions  [PLATFORM]
│   │   ├── users.py                # 446  profile, team, credits, invoices, USERS dict    [PLATFORM+]
│   │   ├── admin.py                # 131  admin dashboard/settings/users                  [PLATFORM]
│   │   ├── setup.py                # 109  first-boot wizard                               [PLATFORM]
│   │   ├── generate.py             # 102  AI generation endpoints (SSE)                   [PRODUCT]
│   │   ├── jira.py                 # 160  Jira connect/projects/issues + Xray push        [PRODUCT]
│   │   └── web.py                  #  92  page routes                                     [MIXED]
│   │
│   ├── core/                       # ── business logic ──
│   │   ├── auth.py                 #   bcrypt + JWT                                        [PLATFORM]
│   │   ├── security.py             # 196  sessions, 2FA, email verification               [PLATFORM]
│   │   ├── settings_service.py     # 131  DB-backed config + Fernet encryption            [PLATFORM]
│   │   ├── linkedin_oauth.py       #  82  LinkedIn OAuth 2.0                               [PLATFORM]
│   │   ├── ai_engine.py            # 154  Anthropic integration, prompt build             [PRODUCT]
│   │   ├── prompt_templates.py     # 319  system prompts (8 generation types)             [PRODUCT]
│   │   ├── layer_resolver.py       # 232  3-layer AI resolution engine                    [PRODUCT]
│   │   ├── knowledge.py            # 115  knowledge-volume loader                          [PRODUCT]
│   │   └── jira_client.py          # 212  Jira REST client (read) + Xray create (write)   [PRODUCT]
│   │
│   ├── models/                     # ── SQLAlchemy models ──
│   │   ├── user.py                 # 137  user, team, credits, invoices                   [PLATFORM]
│   │   ├── generation.py           # 112  jobs, artifacts, platform knowledge             [PRODUCT]
│   │   └── settings.py             #      app_settings table                              [PLATFORM]
│   │
│   ├── schemas/
│   │   └── generate.py             #      pydantic request/response                       [PRODUCT]
│   │
│   └── templates/web/              # ── Jinja2 views ──
│       ├── _base.html              #  nav + shell (extended by most pages)                [PLATFORM]
│       ├── landing.html            # 1108                                                 [PRODUCT]
│       ├── index.html              #  818  standalone generator (does NOT extend _base)   [PRODUCT]
│       ├── generate_issue.html     #  379  per-issue generate page                        [PRODUCT]
│       ├── projects.html / stories.html                                                   [PRODUCT]
│       ├── dashboard / credits / profile / security / team ...                            [PLATFORM]
│       ├── login / register / setup / *_password / two_fa / verify_email ...              [PLATFORM]
│       └── admin_*.html                                                                   [PLATFORM]
│
├── knowledge_volumes/              # 6 markdown volumes (gitignored)                       [PRODUCT]
├── tests/test_veridiq.py           # pytest suite (NEEDS a boot+route smoke test)
├── docs/                           # DESIGN_DOCUMENT, PRODUCT_FEATURES, TECH_STACK
├── requirements.txt · run.bat · Dockerfile · railway.toml
└── HANDOFF.md · CHANGELOG.md · ARCHITECTURE.md · README.md
```

**Tags above** (`[PLATFORM]` / `[PRODUCT]` / `[MIXED]`) mark the natural seam for §3.
Note `users.py` mixes platform (profile/team) with billing (credits/invoices), and
`jira_client.py` mixes read (Jira) with write (Xray) — both are split in the target.

---

## 3. PROPOSED modular target (skeleton + product + delivery)
Goal: a **`platform/` skeleton** that is product-agnostic and copyable to seed new
products, a **`product/`** layer holding only Verid-iq logic, and a thin
**`delivery/`** layer adapting the core to each launch surface.

```
app/
├── main.py                     # composition root only: build app, include routers, lifespan
├── config.py                   # env settings (shared)
│
├── platform/                   # ★ REUSABLE SKELETON — copy this to start a new product
│   ├── db/                     # engine, session, Base, create_tables   (← database.py)
│   ├── settings/               # settings_service + settings model       (DB config + Fernet)
│   ├── auth/                   # bcrypt+JWT, sessions, 2FA, email-verify  (← core/auth, core/security)
│   │   ├── service.py
│   │   ├── routes.py           # generic register/login/2FA              (← api/auth.py)
│   │   └── providers/          # pluggable identity: linkedin_oauth, (future) atlassian
│   ├── users/                  # user/team model + profile/team routes   (← models/user, api/users)
│   ├── billing/                # credits, invoices, top-ups              (split out of api/users)
│   ├── admin/                  # admin routes + templates                (← api/admin)
│   ├── notifications/          # email/SMTP                              (extracted)
│   ├── setup/                  # first-boot wizard                       (← api/setup)
│   └── web/                    # _base.html, nav, static, template utils
│
├── product/                    # ★ VERID-IQ ONLY
│   ├── generation/             # ai_engine, prompt_templates, layer_resolver, knowledge,
│   │                           #   schemas, generate routes
│   ├── integrations/
│   │   ├── jira/               # jira_client READ (projects, issues, get_issue)
│   │   └── xray/               # test-issue create/push (split from jira_client)  ← Tier-3 home
│   └── web/                    # landing, index, projects, stories, generate_issue templates
│
└── delivery/                   # ★ LAUNCH SURFACES — thin adapters over product+platform
    ├── webapp/                 # standalone site (Network Logic subdomain) — current default
    └── atlassian_connect/      # Connect descriptor, lifecycle hooks, Jira iframe panels
        #  (Xray Marketplace reuses the same REST surface; mostly listing/packaging)
```

### Design rules for the skeleton
- **Dependency direction:** `delivery → product → platform`. Platform imports
  nothing from product; product imports nothing from delivery. (Enforced by review.)
- **No HTML in business logic.** Routes/services return data; templating lives in
  `web/` layers. This is what lets the Connect app reuse the same services.
- **Each feature is a package** with its own routes/service/models — so changing
  one feature can't silently break another ("reduce risk of breaking things").
- **Composition root (`main.py`)** is the only place that knows about all modules.
- **Reuse path:** to start a new product, copy `app/platform/` + `config.py` +
  `main.py` skeleton, drop in a new `product/`, done.

---

## 4. Migration plan (incremental, safe — NOT yet started)

> **Owner directive (rock-carved, 2026-06-03): EVOLVE, NEVER BREAK.** Pursue this
> target ONLY via small, behaviour-preserving steps, each behind its own freeze and
> a green smoke test. **No big-bang reorganization.** The repo must never be left
> broken — on GitHub, the laptop, or any host. If a step can't be done safely, stop
> and ask. See `HANDOFF.md` §10.

Refactor only with a green safety net and a freeze per step.

0. **Prereq:** add a **smoke test** (`tests/`) that boots the app and asserts every
   route returns < 500, plus the existing template-render checks. Freeze.
1. Extract `platform/db` + `platform/settings` (lowest-level, no deps). Test. Freeze.
2. Extract `platform/auth` (+providers) and `platform/users`. Test. Freeze.
3. Split `platform/billing` out of users; extract `platform/admin`, `setup`,
   `notifications`. Test. Freeze.
4. Move product code into `product/generation` and split
   `product/integrations/{jira,xray}`. Test. Freeze.
5. Introduce `delivery/webapp` as the current app; stub `delivery/atlassian_connect`.
   Test. Freeze.

Each step is import-path moves + re-wiring `main.py` — behaviour-preserving.
Roll back to the step's freeze if anything regresses.

---

## 5. Status
- §1 vision: **confirmed** by owner (full product, 4 launch surfaces).
- §2 current structure: **accurate** as of `3918eff`.
- §3 target + §4 plan: **proposed, awaiting go-ahead.** Nothing moved yet.
