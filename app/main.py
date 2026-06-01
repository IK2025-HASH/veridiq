# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — AI-Powered Test Intelligence

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from app.config import settings
from app.core.knowledge import knowledge_store
from app.core import settings_service
from app.api import generate, web, users, auth
from app.api.setup import router as setup_router
from app.api.admin import router as admin_router
from app.api.jira import router as jira_router

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

    # Restore admin user from DB so login works after restart
    if app.state.setup_complete:
        try:
            admin_id = await settings_service.get("admin_id")
            admin_email = await settings_service.get("admin_email")
            admin_pw_hash = await settings_service.get("admin_password_hash")
            if admin_id and admin_email and admin_pw_hash:
                from app.api.users import USERS
                import datetime as _dt
                USERS.setdefault(admin_id, {
                    "id": admin_id,
                    "email": admin_email,
                    "display_name": "Admin",
                    "hashed_password": admin_pw_hash,
                    "is_verified": True,
                    "is_active": True,
                    "is_admin": True,
                    "tier": "enterprise",
                    "credit_balance": 1000,
                    "credits_used_month": 0,
                    "credits_used_total": 0,
                    "account_type": "individual",
                    "team_id": None,
                    "classified_mode": False,
                    "billing_name": None,
                    "billing_address": None,
                    "billing_vat": None,
                    "company_name": None,
                    "phone": None,
                    "avatar_url": None,
                    "created_at": _dt.datetime.utcnow().isoformat(),
                    "last_login": None,
                })
                logger.info(f"Admin user restored: {admin_email}")
        except Exception as e:
            logger.warning(f"Could not restore admin user: {e}")

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
