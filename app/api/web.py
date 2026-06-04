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
    return templates.TemplateResponse(request=request, name="web/landing.html",
                                      context={"user": get_current_user(request)})

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


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    from fastapi.responses import RedirectResponse
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request=request, name="web/projects.html", context={"user": user}
    )


@router.get("/projects/{project_key}/stories", response_class=HTMLResponse)
async def stories_page(request: Request, project_key: str):
    from fastapi.responses import RedirectResponse
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="web/stories.html",
        context={"user": user, "project_key": project_key.upper()},
    )


@router.get("/generate/{issue_key}", response_class=HTMLResponse)
async def generate_issue_page(request: Request, issue_key: str):
    from fastapi.responses import RedirectResponse
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
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
        name="web/generate_issue.html",
        context={
            "user": user,
            "issue_key": issue_key.upper(),
            "generation_types": generation_types,
        },
    )
