# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — AI-Powered Test Intelligence

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import auth, generate, users, web
from app.api.admin import router as admin_router
from app.api.jira import router as jira_router
from app.api.setup import router as setup_router
from app.config import settings
from app.core import settings_service, user_repository
from app.core.knowledge import knowledge_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Verid-iq...")

    # Create DB tables (including app_settings)
    from app.database import create_tables
    try:
        await create_tables()
    except Exception as e:
        logger.error(f"create_tables failed (continuing anyway): {e}")

    # Load settings from DB and check setup state
    try:
        await settings_service.load_all()
        app.state.setup_complete = await settings_service.is_setup_complete()
        logger.info(f"Setup complete: {app.state.setup_complete}")
    except Exception as e:
        logger.warning(f"Could not load settings from DB: {e}")
        app.state.setup_complete = False

    # Restore ALL users from user_accounts table into the USERS dict.
    # Falls back to the settings-table path for the admin if the table
    # is empty (e.g. existing install that predates Sprint 3).
    if app.state.setup_complete:
        from app.api.users import USERS
        try:
            db_users = await user_repository.load_all()
            for u in db_users:
                USERS.setdefault(u["id"], u)
            if db_users:
                logger.info(f"Restored {len(db_users)} user(s) from DB")
        except Exception as e:
            logger.warning(f"Could not load users from DB: {e}")

        # Legacy fallback: restore admin from settings table if not yet in user_accounts
        try:
            admin_id = await settings_service.get("admin_id")
            if admin_id and admin_id not in USERS:
                import datetime as _dt
                admin_email = await settings_service.get("admin_email") or ""
                admin_pw_hash = await settings_service.get("admin_password_hash") or ""
                USERS[admin_id] = {
                    "id": admin_id, "email": admin_email, "display_name": "Admin",
                    "hashed_password": admin_pw_hash, "email_verified": True,
                    "is_active": True, "is_admin": True, "tier": "enterprise",
                    "credit_balance": 1000, "credits_used_month": 0,
                    "credits_used_total": 0, "account_type": "individual",
                    "team_id": None, "team_role": None, "classified_mode": False,
                    "billing_name": None, "billing_address": None,
                    "billing_vat": None, "company_name": None,
                    "phone": None, "avatar_url": None, "two_fa_enabled": False,
                    "created_at": _dt.datetime.utcnow().isoformat(), "last_login": None,
                }
                logger.info(f"Admin restored from settings fallback: {admin_email}")
                # Migrate to user_accounts for future restarts
                await user_repository.save(USERS[admin_id])
        except Exception as e:
            logger.warning(f"Could not restore admin via fallback: {e}")

        # Restore Jira credentials for all users who have them
        try:
            for uid, user in list(USERS.items()):
                jira_url = await settings_service.get(f"jira_url__{uid}")
                jira_token = await settings_service.get(f"jira_api_token__{uid}")
                if jira_url and jira_token:
                    user["jira_url"] = jira_url
                    user["jira_email"] = await settings_service.get(f"jira_email__{uid}") or ""
                    user["jira_api_token"] = jira_token
                    user["jira_display_name"] = await settings_service.get(f"jira_display_name__{uid}") or ""
                    logger.info(f"Jira credentials restored for user {uid}")
        except Exception as e:
            logger.warning(f"Could not restore Jira credentials: {e}")

    # Load knowledge volumes
    knowledge_dir = Path(__file__).parent.parent / "knowledge_volumes"
    knowledge_store.load(knowledge_dir)
    if knowledge_store.is_loaded:
        logger.info(f"Knowledge volumes loaded: {knowledge_store.volume_names}")
    else:
        logger.warning("No knowledge volumes found — AI will run without domain context")

    logger.info(f"Verid-iq v{settings.VERSION} ready | {settings.ENVIRONMENT}")
    yield
    logger.info("Shutting down Verid-iq...")


app = FastAPI(
    title="Verid-iq",
    description="AI-Powered Test Intelligence — by Network Logic Limited",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["https://veridiq.networklogic.uk"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup guard — redirect everything to /setup until first-boot is complete
SKIP_PATHS = ("/setup", "/static", "/api/health", "/favicon")


@app.middleware("http")
async def setup_guard(request: Request, call_next):
    if any(request.url.path.startswith(p) for p in SKIP_PATHS):
        return await call_next(request)
    if not getattr(request.app.state, "setup_complete", True):
        return RedirectResponse("/setup", status_code=302)
    return await call_next(request)


# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routers
app.include_router(setup_router)
app.include_router(admin_router)
app.include_router(generate.router, prefix="/api", tags=["generation"])
app.include_router(jira_router, prefix="/api", tags=["jira"])
app.include_router(auth.router, tags=["auth"])
app.include_router(users.router, tags=["users"])
app.include_router(web.router, tags=["web"])
