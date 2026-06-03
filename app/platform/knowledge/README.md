# `knowledge/` — Knowledge Management

Manages the domain knowledge that powers the AI (the "knowledge volumes" feeding
Layers 1–2 of the 3-layer engine).

> Status: scaffold. Today a read-only loader exists at `app/core/knowledge.py`
> (loads markdown volumes from `knowledge_volumes/`). This module grows that into
> a managed capability. Implementation lands incrementally behind freezes.

## Responsibilities
- **Storage** of knowledge volumes (currently 6 testing markdown volumes; gitignored).
- **Versioning** — track changes so AI behaviour is reproducible/auditable.
- **CRUD + admin UI** — upload, edit, enable/disable, preview volumes (in `admin/`).
- **Retrieval** — serve relevant chunks to the generation engine (consumed by
  `product/generation/`).
- **Scoping** — global (shipped) vs customer-private knowledge (important for
  on-prem customers who add their own standards/templates).
- **Access control** — who can read/edit knowledge (ties to `users/` roles).

## Notes
- The MANAGEMENT capability is product-agnostic (platform). The CONTENT (testing
  volumes) is Verid-iq-specific and is supplied by the product.
- On-prem customers must be able to manage their OWN knowledge without internet.

## Migrates from
- `app/core/knowledge.py` (loader) — becomes the retrieval half of this module.
