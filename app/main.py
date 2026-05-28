# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — AI-Powered Test Intelligence
# Network Logic Limited | veridiq.networklogic.uk

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from app.config import settings
from app.core.knowledge import knowledge_store
from app.api import generate, web, users, auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Starting Verid-iq...")

    # Load knowledge volumes
    knowledge_dir = Path(__file__).parent.parent / "knowledge_volumes"
    knowledge_store.load(knowledge_dir)

    if knowledge_store.is_loaded:
        logger.info(f"Knowledge volumes loaded: {knowledge_store.volume_names}")
    else:
        logger.warning("No knowledge volumes found — AI will generate without domain context")

    logger.info(f"Verid-iq v{settings.VERSION} ready | {settings.ENVIRONMENT}")
    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down Verid-iq...")


app = FastAPI(
    title="Verid-iq",
    description="AI-Powered Test Intelligence for Jira — by Network Logic Limited",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["https://veridiq.networklogic.uk"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Static files ──────────────────────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(generate.router, prefix="/api", tags=["generation"])
app.include_router(auth.router, tags=["auth"])
app.include_router(users.router, tags=["users"])
app.include_router(web.router, tags=["web"])
