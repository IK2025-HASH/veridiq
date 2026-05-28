# Verid-iq — Design Document

> System Architecture, Data Models & API Design

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Browser (Jinja2 HTML + Vanilla JS)   │   Jira Connect Plugin    │
└────────────────────┬─────────────────────────────┬──────────────┘
                     │ HTTP / SSE                   │ HTTP
┌────────────────────▼─────────────────────────────▼──────────────┐
│                     FASTAPI APPLICATION                          │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐  │
│  │ /api/       │  │ /auth/      │  │ /users/  │  │ /web/    │  │
│  │ generate    │  │ auth router │  │ users    │  │ pages    │  │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └──────────┘  │
│         │                │              │                        │
│  ┌──────▼──────────────────────────────▼──────────────────────┐ │
│  │                    CORE SERVICES                           │ │
│  │  ai_engine │ layer_resolver │ auth │ security │ knowledge  │ │
│  └──────┬────────────┬─────────────────────────────────────── ┘ │
│         │            │                                           │
└─────────┼────────────┼───────────────────────────────────────── ┘
          │            │
┌─────────▼──┐   ┌─────▼───────────────────┐
│ Anthropic  │   │   PostgreSQL Database    │
│ Claude API │   │  (SQLAlchemy + asyncpg)  │
└────────────┘   └─────────────────────────┘
```

---

## 2. Application Structure

```
veridiq/
├── app/
│   ├── main.py               # FastAPI app, middleware, lifespan
│   ├── config.py             # Pydantic Settings (env-driven)
│   ├── database.py           # Async SQLAlchemy engine + session
│   ├── api/
│   │   ├── generate.py       # AI generation endpoints
│   │   ├── auth.py           # Auth flows (login, register, OAuth, 2FA)
│   │   ├── users.py          # User/team/credits/invoices
│   │   └── web.py            # Jinja2 page routes
│   ├── core/
│   │   ├── ai_engine.py      # Anthropic streaming + full generation
│   │   ├── layer_resolver.py # 3-layer resolution engine
│   │   ├── prompt_templates.py # System roles + generation instructions
│   │   ├── knowledge.py      # Knowledge volume loader + matcher
│   │   ├── auth.py           # JWT + bcrypt utilities
│   │   ├── security.py       # 2FA, email tokens, session store
│   │   └── linkedin_oauth.py # LinkedIn OpenID Connect
│   ├── models/
│   │   ├── user.py           # UserAccount, Team, CreditTxn, Invoice
│   │   └── generation.py     # User, Team, GenerationJob, Artifact, UserContext, PlatformKnowledge
│   ├── schemas/
│   │   └── generate.py       # Pydantic request/response schemas
│   ├── static/               # CSS, JS assets
│   └── templates/web/        # Jinja2 HTML templates
├── knowledge_volumes/        # Markdown domain knowledge files
├── alembic/                  # Database migrations
├── tests/                    # pytest test suite
├── Dockerfile
├── railway.toml
└── requirements.txt
```

---

## 3. Data Models

### UserAccount
```
UserAccount
├── id              UUID (PK)
├── email           String (unique)
├── display_name    String
├── hashed_password String
├── is_verified     Boolean (default: False)
├── created_at      DateTime
└── team_id         UUID (FK → Team)
```

### Team
```
Team
├── id              UUID (PK)
├── name            String
├── description     String
├── credit_balance  Integer
├── owner_id        UUID (FK → UserAccount)
└── created_at      DateTime
```

### TeamInvite
```
TeamInvite
├── id              UUID (PK)
├── team_id         UUID (FK → Team)
├── email           String
├── role            String
├── token           String (unique)
└── created_at      DateTime
```

### CreditTxn
```
CreditTxn
├── id              UUID (PK)
├── team_id         UUID (FK → Team)
├── amount          Integer (+/-)
├── description     String
└── created_at      DateTime
```

### Invoice
```
Invoice
├── id              UUID (PK)
├── team_id         UUID (FK → Team)
├── amount_gbp      Numeric
├── credits         Integer
├── status          String
└── created_at      DateTime
```

### GenerationJob
```
GenerationJob
├── id              UUID (PK)
├── user_id         UUID (FK → User)
├── generation_type String
├── input_text      Text
├── layer_used      Integer (1/2/3)
├── credits_used    Integer
├── duration_ms     Integer
└── created_at      DateTime
```

### Artifact
```
Artifact
├── id              UUID (PK)
├── job_id          UUID (FK → GenerationJob)
├── content         Text
├── approved        Boolean
└── created_at      DateTime
```

### UserContext (Layer 1 cache)
```
UserContext
├── id              UUID (PK)
├── user_id         UUID (FK → User)
├── generation_type String
├── input_hash      String
├── output          Text
└── created_at      DateTime
```

### PlatformKnowledge (Layer 2 cache)
```
PlatformKnowledge
├── id              UUID (PK)
├── generation_type String
├── topic           String
├── content         Text
└── confidence      Float
```

---

## 4. API Design

### Generation API

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/generate/stream` | SSE streaming generation (real-time token output) |
| `POST` | `/api/generate` | Full JSON generation (complete response) |
| `GET` | `/api/generation-types` | List all available generation types |
| `GET` | `/api/health` | Health check |

**GenerateRequest schema:**
```json
{
  "generation_type": "TEST_CASES",
  "input_text": "As a user I want to login...",
  "quantity": 3
}
```

### Auth API

| Method | Route | Description |
|---|---|---|
| `POST` | `/register` | Email registration |
| `POST` | `/login` | Email login |
| `POST` | `/api/auth/logout` | Logout |
| `GET` | `/auth/linkedin` | LinkedIn OAuth redirect |
| `GET` | `/auth/linkedin/callback` | LinkedIn OAuth callback |
| `POST` | `/api/auth/forgot-password` | Send reset email |
| `POST` | `/api/auth/reset-password` | Reset with token |
| `POST` | `/api/auth/2fa/enable` | Enable TOTP 2FA |
| `POST` | `/api/auth/2fa/verify` | Verify 2FA token |
| `GET` | `/security` | Sessions list |
| `POST` | `/api/auth/sessions/{id}/revoke` | Revoke session |

### Users API

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/users/me` | Current user profile |
| `POST` | `/api/users/me` | Update profile |
| `POST` | `/api/teams` | Create team |
| `POST` | `/api/teams/invite` | Invite member |
| `GET` | `/api/credits/balance` | Credit balance |
| `POST` | `/api/credits/topup` | Purchase credits |
| `GET` | `/api/invoices` | List invoices |

---

## 5. Authentication Flow

```
Email Registration:
POST /register → hash password → create user (unverified) → send verification email
    → GET /auth/verify-email/{token} → mark verified → redirect to login

Email Login:
POST /login → verify password → check 2FA enabled?
    → No 2FA:  create JWT + session → set cookie → redirect dashboard
    → 2FA on:  create pending token → redirect to 2FA verify page
               → POST /api/auth/2fa/verify → validate TOTP → create JWT + session

LinkedIn OAuth:
GET /auth/linkedin → redirect to LinkedIn with CSRF state
    → callback with code → exchange for token → fetch profile
    → upsert user → create JWT + session → redirect dashboard
```

---

## 6. Generation Flow (SSE Streaming)

```
POST /api/generate/stream
    │
    ├─► Layer Resolver: check user context (Layer 1)
    │       ├─ hit  → stream cached content (0 credits)
    │       └─ miss ↓
    ├─► Layer Resolver: check platform knowledge (Layer 2)
    │       ├─ hit  → stream knowledge content (1 credit)
    │       └─ miss ↓
    └─► AI Engine: build prompt → call Anthropic stream API
            → yield tokens via SSE → deduct credits → store in DB
```

---

## 7. Security Design

| Concern | Implementation |
|---|---|
| Password storage | bcrypt (passlib) |
| Session tokens | JWT HS256 (24h access / 30d refresh) |
| 2FA | TOTP via pyotp (RFC 6238) |
| Email tokens | Cryptographic random secrets (secrets module) |
| CSRF (OAuth) | In-memory state store per OAuth request |
| Rate limiting | slowapi (per IP, per day) |
| CORS | Restricted to production domain in non-dev environments |
| API docs | Disabled in production (`docs_url=None`) |

---

## 8. Configuration (Environment Variables)

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `DATABASE_URL` | — | PostgreSQL async URL |
| `SECRET_KEY` | — | JWT signing secret |
| `ENVIRONMENT` | `production` | `development` enables API docs + relaxed CORS |
| `RATE_LIMIT_PER_DAY` | `5` | Max generations per IP per day |
| `LINKEDIN_CLIENT_ID` | — | LinkedIn OAuth app ID |
| `LINKEDIN_CLIENT_SECRET` | — | LinkedIn OAuth secret |
| `SMTP_HOST/PORT/USER/PASSWORD` | — | Email delivery settings |
| `BASE_URL` | `https://veridiq.networklogic.uk` | Used in email links |

---

## 9. Deployment Architecture

```
 Railway Platform
 ┌──────────────────────────────────┐
 │  Service: veridiq                │
 │  Builder: Nixpacks               │
 │  Start: uvicorn --workers 2      │
 │  Health: GET /api/health         │
 │  Restart: ON_FAILURE (max 3)     │
 └──────────────┬───────────────────┘
                │
 ┌──────────────▼───────────────────┐
 │  PostgreSQL (Railway add-on)     │
 │  DATABASE_URL injected at boot   │
 └──────────────────────────────────┘
```

---

## 10. Known Technical Debt

| Item | Location | Notes |
|---|---|---|
| In-memory user/session stores | `api/auth.py`, `core/security.py` | Must be replaced with DB before production scale |
| Duplicate model sets | `models/user.py` vs `models/generation.py` | `User`/`Team` defined twice — needs consolidation |
| Missing `artifact` model import | `database.py` | `from app.models import artifact` will fail |
| No credit deduction on generation | `api/generate.py` | Credits shown but not actually deducted yet |
| SMTP not wired | `core/security.py` | Email sending implemented but not tested end-to-end |
