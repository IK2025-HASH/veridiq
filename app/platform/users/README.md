# `users/` — User Management

Manages identities, roles, teams, and profiles for both SaaS and on-prem modes.

> Status: scaffold. Working code lives in `app/api/users.py` (+ `app/models/user.py`).
> NOTE: in Milestone 1, users (except admin) are held in an **in-memory dict** and
> do NOT persist across restart — see HANDOFF.md §4. Making users DB-backed and
> persistent is a primary goal of this module.

## Responsibilities
- User lifecycle: create, invite, activate/deactivate, delete.
- **Roles & permissions** — e.g. System Admin, License Admin, Knowledge Manager,
  Tester/End User (see `RACI.md`). Drives feature/route authorization.
- Teams / organisations and membership.
- Profile management.
- **Seat coordination** with `licensing/` — enforce the licensed max-user cap on-prem.

## Migrates from
- `app/models/user.py` (model), `app/api/users.py` (routes — billing parts move to `billing/`).

## Key change vs today
- Persist users in the DB (SQLite local / Postgres on Railway / customer DB on-prem)
  instead of the in-memory `USERS` dict.
