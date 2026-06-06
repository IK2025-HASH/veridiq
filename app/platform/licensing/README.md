# `licensing/` — License Management (NEW)

Enables Verid-iq (and future products) to be **sold as an on-premise instance
licence**, where the customer hosts the software themselves.

> Status: scaffold. Design captured here; implementation pending and will land
> incrementally behind freezes.

## Why this exists
Three distribution modes must be supported by ONE codebase:
1. **SaaS (multi-tenant)** — Network Logic hosts; billing via credits (see `billing/`).
2. **On-premise instance licence** — customer hosts; access governed by a licence key.
3. **Marketplace apps** (Atlassian / Xray) — vendor-managed entitlements.

`licensing/` governs mode 2 (and gates features regardless of mode).

## Core responsibilities
- **Licence key** issuance + validation. Signed (asymmetric) so an on-prem instance
  can validate **offline** without phoning home. Public key ships in the build;
  private signing key stays with Network Logic.
- **Activation / fingerprinting** — bind a licence to an instance (host id) to deter
  copying; support deactivation/transfer.
- **Entitlements** encoded in the licence: edition/tier, **seat count** (max users),
  feature flags, **expiry / maintenance window**, customer identity.
- **Seat enforcement** — coordinate with `users/` to cap active users.
- **Feature gating** — a single `is_enabled(feature)` / `require_feature(...)` API
  consumed across the app.
- **Grace & expiry** — read-only / warning states when a licence lapses; never hard-crash.
- **Admin surface** — view licence status, apply a new key, see seats used (in `admin/`).

## Design notes / decisions to make later
- Key format: signed JWT or a compact signed token (Ed25519). Decide at build time.
- Offline-first: validation must work with no outbound network (on-prem requirement).
- Clock-tamper tolerance for expiry checks.
- Keep secrets out of the repo — only the **public** verification key is shipped.

## Open questions for the owner (do not assume)
- Editions/tiers and what each unlocks?
- Per-seat vs per-instance pricing? Default seat cap?
- Licence term: perpetual + maintenance, or annual subscription?
- Hard expiry vs grace period length?
