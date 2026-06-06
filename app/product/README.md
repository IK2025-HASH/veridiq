# `product/` — Verid-iq-specific code

Everything here is unique to Verid-iq. It depends on `platform/` but `platform/`
never depends on it.

> Status: scaffold. Working code lives under `app/api/` and `app/core/`; migrated
> here incrementally behind freezes (ARCHITECTURE.md §4).

## Modules
| Package | Responsibility | Migrates from |
|---|---|---|
| `generation/` | AI engine, prompt templates, 3-layer resolver, knowledge consumption, generate routes/schemas | `app/core/ai_engine.py`, `prompt_templates.py`, `layer_resolver.py`, `app/api/generate.py`, `app/schemas/generate.py` |
| `integrations/jira/` | Jira READ — projects, issues, issue detail | read half of `app/core/jira_client.py` + `app/api/jira.py` |
| `integrations/xray/` | Xray WRITE — push approved tests as issues (**Tier 3 lives here**) | write half of `app/core/jira_client.py` |

The Jira/Xray split mirrors the seam already visible in `jira_client.py` (read vs write).
