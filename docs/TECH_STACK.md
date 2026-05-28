# Verid-iq — Technology Stack

> Network Logic Limited | veridiq.networklogic.uk

---

## Summary

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web Framework | FastAPI 0.111 |
| AI Provider | Anthropic Claude (claude-sonnet-4-20250514) |
| Database | PostgreSQL 15+ |
| ORM | SQLAlchemy 2.0 (async) |
| DB Driver | asyncpg 0.29 |
| Migrations | Alembic 1.13 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| 2FA | TOTP (pyotp) |
| Templating | Jinja2 3.1 |
| Rate Limiting | slowapi 0.1.9 |
| HTTP Client | httpx 0.27 |
| Validation | Pydantic v2 + pydantic-settings |
| Hosting | Railway |
| Container | Docker (python:3.11-slim) |
| Build | Nixpacks (Railway) |
| Testing | pytest + pytest-asyncio |

---

## Backend

### Python 3.11
- Stable LTS release with broad package wheel support
- Full async/await support
- Used for all server-side logic

### FastAPI 0.111
- High-performance ASGI framework built on Starlette
- Automatic OpenAPI/Swagger docs (enabled in development)
- Native async support — matches async DB and AI streaming
- Server-Sent Events (SSE) for real-time AI token streaming
- Dependency injection for DB sessions and auth
- Pydantic v2 integration for request/response validation

### Anthropic Claude SDK 0.26
- Official Python SDK for Claude AI
- Streaming API used for real-time generation output
- Model: `claude-sonnet-4-20250514` — high quality, fast, cost-effective
- `AsyncAnthropic` client for non-blocking calls
- Handles: `APIConnectionError`, `RateLimitError`, `APIStatusError`

---

## Database

### PostgreSQL
- Primary data store for users, teams, credits, generations, artefacts
- UUID primary keys throughout
- Railway managed in production (auto-provisioned `DATABASE_URL`)

### SQLAlchemy 2.0 (Async)
- Modern async ORM with `AsyncSession` and `async_sessionmaker`
- `DeclarativeBase` for model definitions
- `pool_pre_ping=True` for connection resilience
- `create_async_engine` with asyncpg driver

### asyncpg 0.29
- High-performance native PostgreSQL async driver
- Used via SQLAlchemy's `postgresql+asyncpg://` URL scheme

### psycopg2-binary
- Used by Alembic migrations (sync operations only)

### Alembic 1.13
- Database migration management
- Version-controlled schema changes
- Run: `alembic upgrade head`

---

## Authentication & Security

### python-jose 3.3 (JWT)
- JSON Web Token creation and verification
- Algorithm: HS256
- Access tokens: 24-hour expiry
- Refresh tokens: 30-day expiry
- Token payload: `sub` (user_id), `email`, `exp`, `type`

### passlib 1.7 + bcrypt
- Secure password hashing using bcrypt
- `CryptContext` with automatic deprecation handling
- Never stores plaintext passwords

### pyotp 2.9
- RFC 6238 TOTP implementation for 2FA
- Compatible with Google Authenticator, Authy, 1Password
- QR code provisioning URI generation

### cryptography 42
- Underlying cryptographic primitives
- Used by jose and other security packages

---

## Frontend

### Jinja2 3.1
- Server-side HTML templating
- Shared `_base.html` layout with block inheritance
- Pages: landing, index, login, register, dashboard, profile, credits, security, terms, privacy
- No separate frontend build step — HTML served directly by FastAPI

### Vanilla JavaScript
- No frontend framework (React/Vue/etc.) — intentional simplicity
- SSE (`EventSource`) for streaming AI output to the browser
- Fetch API for form submissions
- Static files served from `app/static/`

---

## HTTP & Networking

### httpx 0.27
- Async HTTP client
- Used for LinkedIn OAuth token exchange and profile fetch
- Timeout handling for external API calls

### slowapi 0.1.9
- Rate limiting middleware for FastAPI
- Built on `limits` library
- Key function: `get_remote_address` (IP-based)
- Configurable limit: `RATE_LIMIT_PER_DAY` generations per day

---

## Validation & Settings

### Pydantic v2 2.7
- Request/response schema validation
- `GenerateRequest`, `GenerateResponse` schemas
- `Literal` types for `GenerationType` enum
- `Field` constraints: `min_length`, `max_length`, `ge`, `le`

### pydantic-settings 2.2
- Environment variable loading into typed `Settings` class
- `.env` file support via `env_file` config
- `@lru_cache` singleton pattern for settings instance

---

## Deployment

### Railway
- PaaS hosting with automatic deployments from GitHub
- Nixpacks builder: auto-detects Python, installs deps, starts app
- Managed PostgreSQL add-on with automatic `DATABASE_URL` injection
- Environment variables set via Railway dashboard
- Health check: `GET /api/health`
- Restart policy: `ON_FAILURE`, max 3 retries
- Production URL: `https://veridiq.networklogic.uk`

### Docker
- Base image: `python:3.11-slim` (minimal footprint)
- System deps: `gcc`, `libpq-dev` (for psycopg2)
- 2 uvicorn workers in production
- Port: 8000 (Railway maps to HTTPS 443)

### uvicorn 0.29
- ASGI server for FastAPI
- `--reload` flag in development (hot reload)
- `--workers 2` in production (Railway/Docker)
- `[standard]` extras: websockets, watchfiles, httptools

---

## Testing

### pytest 8.2
- Test runner
- Test file: `tests/test_veridiq.py`

### pytest-asyncio 0.23
- Async test support for FastAPI + SQLAlchemy async code

---

## AI Model Details

| Property | Value |
|---|---|
| Provider | Anthropic |
| Model | claude-sonnet-4-20250514 |
| Max tokens | 4,096 |
| Interface | Streaming (`client.messages.stream`) + Full (`client.messages.create`) |
| Context | System prompt (role) + knowledge chunks + user input |
| Knowledge injection | Up to 6 domain knowledge volumes loaded at startup |

---

## Dependency Reference

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
anthropics==0.26.0
sqlalchemy==2.0.30
alembic==1.13.1
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
jinja2==3.1.4
python-multipart==0.0.9
slowapi==0.1.9
httpx==0.27.0
pydantic==2.7.1
pydantic-settings==2.2.1
cryptography==42.0.7
pytest==8.2.0
pytest-asyncio==0.23.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pyotp==2.9.0
```
