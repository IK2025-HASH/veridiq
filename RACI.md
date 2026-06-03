# RACI — Verid-iq

A RACI matrix clarifies, for each activity, who is:
- **R — Responsible:** does the work.
- **A — Accountable:** owns the outcome / signs off (one per row).
- **C — Consulted:** gives input before it happens.
- **I — Informed:** told after it happens.

This is a living document. It serves two purposes: (1) define **runtime product
roles** (which drives `platform/users/` roles & permissions), and (2) define
**build & delivery responsibilities** while the product is created.

---

## A. Runtime / operational RACI (product roles)
These roles drive the permission model in `platform/users/` and feature gating in
`platform/licensing/`. On-prem, one person may hold several roles.

**Roles:** SA = System Admin · LA = Licence Admin · KM = Knowledge Manager ·
TL = Team Lead/Manager · QA = Tester / End User

| Activity | SA | LA | KM | TL | QA |
|---|---|---|---|---|---|
| Install / host the instance (on-prem) | A/R | C | I | – | – |
| Configure instance settings (API keys, SMTP) | A/R | I | – | – | – |
| Apply / renew **licence key**, manage seats | C | A/R | – | I | I |
| Create / invite / deactivate **users** | C | C | – | A/R | – |
| Assign roles & permissions | A/R | C | – | C | – |
| Manage **knowledge volumes** (upload, version, enable) | C | – | A/R | C | I |
| Connect **Jira** account (own credentials) | I | – | – | C | A/R |
| Browse projects / stories | – | – | – | I | A/R |
| **Generate** test artifacts (AI) | – | – | C | I | A/R |
| **Review & approve** an artifact | – | – | C | A | R |
| **Push** approved artifact to Jira/Xray | – | – | – | I | A/R |
| Manage billing / credits (SaaS mode) | C | A/R | – | I | I |
| View audit / usage reports | A/R | C | – | C | I |

Principle: **the human (QA) is Accountable for approving anything before it leaves
the tool.** AI drafts; the tester signs off.

---

## B. Build & delivery RACI (while we create the product)
**Actors:** Owner = Ilyas Kadri · AI = Claude (AI assistant) · Future = future contributors

| Activity | Owner | AI | Future |
|---|---|---|---|
| Product vision, scope, priorities | A/R | C | I |
| Go-to-market (LinkedIn, Atlassian, Xray, subdomain) | A/R | C | I |
| Licensing model & pricing decisions | A/R | C | I |
| Architecture decisions (modular target) | A | R | C |
| Implementation / coding | A | R | – |
| Running & testing changes locally | A/R | C | – |
| Freeze points & release tagging | A | R | I |
| Writing/maintaining docs (HANDOFF, ARCHITECTURE, CHANGELOG, this) | A | R | I |
| Approving merges to `main` | A/R | C | – |
| Security review (secrets, licence keys) | A | R | C |

Principle: **Owner is Accountable for every outcome; AI is Responsible for doing
the work under direction and must run/verify before claiming done.**

---

## Notes
- Keep this in sync with `platform/users/` (roles) and `platform/licensing/`
  (entitlements) as they are implemented.
- Roles are capabilities, not job titles — on-prem, a single admin often = SA+LA+KM+TL.
