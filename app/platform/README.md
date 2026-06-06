# `platform/` — Reusable product-agnostic skeleton

★ **This is the scaffold to copy when starting a new Network Logic product.**

Nothing here is Verid-iq-specific. It provides the capabilities every product
needs: database, settings, authentication, user management, licensing, billing,
knowledge management, admin, notifications, and first-boot setup.

> **Status: scaffold.** These packages are placeholders. The working code still
> lives under `app/api/` and `app/core/` and is migrated here **incrementally**,
> one freeze-per-step (ARCHITECTURE.md §4) — never a big-bang move. The app boots
> and behaves identically while this skeleton sits alongside.

## Modules
| Package | Responsibility | Migrates from |
|---|---|---|
| `db/` | Engine, session, Base, `create_tables` | `app/database.py` |
| `settings/` | DB-backed config + Fernet encryption | `app/core/settings_service.py`, `app/models/settings.py` |
| `auth/` | bcrypt, JWT, sessions, 2FA, email-verify | `app/core/auth.py`, `app/core/security.py`, `app/api/auth.py` |
| `auth/providers/` | Pluggable identity (LinkedIn; future Atlassian) | `app/core/linkedin_oauth.py` |
| `users/` | **User management** — users, roles, teams, profiles | `app/api/users.py`, `app/models/user.py` |
| `licensing/` | **License management** — on-prem keys, seats, gating | NEW (see `licensing/README.md`) |
| `knowledge/` | **Knowledge management** — store/version/serve volumes | `app/core/knowledge.py` + NEW admin/CRUD |
| `billing/` | Credits, invoices, top-ups (SaaS mode) | split from `app/api/users.py` |
| `admin/` | Admin console | `app/api/admin.py` |
| `notifications/` | Email / SMTP | extracted from auth/security |
| `setup/` | First-boot wizard | `app/api/setup.py` |

## Rule
Dependency direction is **`delivery → product → platform`**. Platform must NOT
import from `product/` or `delivery/`.
