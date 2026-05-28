# Verid-iq

**AI-Powered Test Intelligence** — by Network Logic Limited  
*AI drafts. You review. Your expertise, accelerated.*

---

## What is Verid-iq?

Verid-iq is an AI-assisted software testing platform that generates professional test cases, BDD scenarios, defect reports, exploratory charters, and more — directly from your user stories and acceptance criteria.

Built as a Python/FastAPI web application and Atlassian Connect app for Jira, distributed on the Atlassian Marketplace and SmartBear Marketplace.

---

## Architecture

```
veridiq/
├── app/
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Settings (env-driven)
│   ├── database.py               # Async PostgreSQL
│   ├── api/
│   │   ├── auth.py               # Registration, LinkedIn OAuth, 2FA, sessions
│   │   ├── users.py              # Profile, team, credits, invoices
│   │   ├── generate.py           # AI generation endpoints (streaming SSE)
│   │   └── web.py                # Page routes
│   ├── core/
│   │   ├── ai_engine.py          # Anthropic API integration
│   │   ├── layer_resolver.py     # 3-layer AI resolution engine
│   │   ├── knowledge.py          # Knowledge volume loader
│   │   ├── prompt_templates.py   # System prompts (8 generation types)
│   │   ├── auth.py               # JWT / password utilities
│   │   ├── security.py           # 2FA, sessions, email verification
│   │   └── linkedin_oauth.py     # LinkedIn OAuth 2.0
│   ├── models/
│   │   ├── generation.py         # DB models (jobs, artifacts, platform knowledge)
│   │   └── user.py               # User, team, credits, invoices
│   └── templates/web/            # Jinja2 HTML templates
├── knowledge_volumes/            # Upload 6 knowledge volumes here (not in git)
├── tests/                        # pytest test suite
├── requirements.txt
├── railway.toml                  # Railway deployment config
└── .env.example                  # Environment variable template
```

---

## Quick Start

```bash
git clone https://github.com/IK2025-HASH/veridiq.git
cd veridiq
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000/landing

---

## Knowledge Volumes

Place the 6 Verid-iq knowledge Markdown files in `knowledge_volumes/`:

- `vol1_testing_standards.md`
- `vol2_test_design_techniques.md`
- `vol3_bdd_gherkin.md`
- `vol4_test_management.md`
- `vol5_jira_xray_confluence.md`
- `vol6_security_testing.md`

These are excluded from git (`.gitignore`). Upload separately.

---

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://user:pass@host/veridiq
SECRET_KEY=your-secret-key
ENVIRONMENT=production

# LinkedIn OAuth (optional)
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=https://veridiq.networklogic.uk/auth/linkedin/callback

# Email / SMTP (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=no-reply@networklogic.uk

BASE_URL=https://veridiq.networklogic.uk
```

---

## Deploy to Railway

1. Connect this repo to Railway
2. Add environment variables (Settings → Variables)
3. Railway auto-deploys on every push to `main`
4. Domain: configure `veridiq.networklogic.uk` in Railway settings

---

## 3-Layer AI Architecture

| Layer | Source | Cost |
|---|---|---|
| Layer 1 | User's own prior context | 0 credits |
| Layer 2 | Anonymised platform knowledge | 1 credit |
| Layer 3 | Anthropic AI (full generation) | 3–10 credits |

---

## Features

- 8 AI generation types (Test Cases, BDD, Defect Reports, Test Plans, and more)
- Batch generation with n= parameter
- 3-layer AI with credit economy
- Email + LinkedIn OAuth registration
- TOTP two-factor authentication
- Session management
- Team management with shared credit pools
- Credit-based pricing with live dashboard
- Invoice generation
- Atlassian Connect app (Jira panel + Xray push)
- Human-in-the-loop by design

---

## Marketplaces

- **Atlassian Marketplace** — Jira Cloud, Test Management category
- **SmartBear Marketplace** — Xray ecosystem

---

## License & Copyright

© 2026 Network Logic Limited. All rights reserved.  
Verid-iq is a registered trade mark of Network Logic Limited.  
Unauthorised use, copying, or distribution is strictly prohibited.
