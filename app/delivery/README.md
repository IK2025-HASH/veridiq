# `delivery/` — Launch surfaces (thin adapters)

Each delivery surface is a thin adapter that composes `product/` + `platform/`
into a runnable/embeddable app. Surfaces hold NO business logic.

> Status: scaffold. The current app is the standalone web app wired in
> `app/main.py`; it becomes `webapp/`. `atlassian_connect/` is a stub for the
> Jira Marketplace app.

## Surfaces (maps to the 4 go-to-market channels + on-prem)
| Package | Channel |
|---|---|
| `webapp/` | Network Logic subdomain (standalone site); also the **on-prem instance** deployment |
| `atlassian_connect/` | Atlassian Marketplace — Jira Cloud app (iframe panels, Connect lifecycle) |
| _(reuse)_ | Xray Marketplace reuses the same REST surface; mostly listing/packaging |
| _(LinkedIn)_ | LinkedIn community is marketing → drives sign-ups to `webapp/`, not a code surface |

## Rule
`delivery → product → platform`. A surface may import product + platform; never
the reverse.
