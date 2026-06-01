# Copyright © 2026 Network Logic Limited. All rights reserved.

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core.ai_engine import GENERATION_LABELS, GENERATION_ICONS, BATCH_TYPES
from app.api.users import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse(request=request, name="web/terms.html")

@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(request=request, name="web/privacy.html")

@router.get("/landing", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="web/landing.html")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    generation_types = [
        {
            "key": key,
            "label": label,
            "icon": GENERATION_ICONS.get(key, "🔧"),
            "supports_quantity": key in BATCH_TYPES,
        }
        for key, label in GENERATION_LABELS.items()
    ]
    return templates.TemplateResponse(
        request=request,
        name="web/index.html",
        context={"generation_types": generation_types, "user": get_current_user(request)},
    )
