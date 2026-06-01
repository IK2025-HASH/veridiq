# Copyright © 2026 Network Logic Limited. All rights reserved.
# Admin module — settings management, user overview, credit grants.

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core import settings_service
from app.core.auth import decode_token

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


async def _require_admin(request: Request):
    """Return the user dict if the request carries a valid admin token, else None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    from app.api.users import USERS
    user = next((u for u in USERS.values() if u["id"] == payload.get("sub")), None)
    if not user or not user.get("is_admin"):
        return None
    return user


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = await _require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    from app.api.users import USERS
    stats = {
        "total_users": len(USERS),
        "api_key_set": bool(await settings_service.get("anthropic_api_key")),
        "smtp_set": bool(await settings_service.get("smtp_host")),
        "admin_email": await settings_service.get("admin_email"),
    }
    return templates.TemplateResponse(request=request, name="web/admin_dashboard.html", context={
        "user": user,
        "stats": stats,
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = await _require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    api_key = await settings_service.get("anthropic_api_key") or ""
    current = {
        "anthropic_api_key_masked": (api_key[:12] + "..." + api_key[-4:]) if api_key else "",
        "anthropic_model": await settings_service.get("anthropic_model") or "claude-sonnet-4-20250514",
        "smtp_host": await settings_service.get("smtp_host") or "",
        "smtp_port": await settings_service.get("smtp_port") or "587",
        "smtp_user": await settings_service.get("smtp_user") or "",
        "linkedin_client_id": await settings_service.get("linkedin_client_id") or "",
        "rate_limit_per_day": await settings_service.get("rate_limit_per_day") or "5",
    }
    return templates.TemplateResponse(request=request, name="web/admin_settings.html", context={
        "user": user,
        "current": current,
        "saved": request.query_params.get("saved"),
    })


@router.post("/settings")
async def settings_save(
    request: Request,
    anthropic_api_key: str = Form(default=""),
    anthropic_model: str = Form(default="claude-sonnet-4-20250514"),
    smtp_host: str = Form(default=""),
    smtp_port: str = Form(default="587"),
    smtp_user: str = Form(default=""),
    smtp_password: str = Form(default=""),
    linkedin_client_id: str = Form(default=""),
    linkedin_client_secret: str = Form(default=""),
    rate_limit_per_day: str = Form(default="5"),
):
    user = await _require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    updates: dict[str, str] = {
        "anthropic_model": anthropic_model,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "rate_limit_per_day": rate_limit_per_day,
        "linkedin_client_id": linkedin_client_id,
    }
    if anthropic_api_key.strip().startswith("sk-ant-"):
        updates["anthropic_api_key"] = anthropic_api_key.strip()
    if smtp_password:
        updates["smtp_password"] = smtp_password
    if linkedin_client_secret:
        updates["linkedin_client_secret"] = linkedin_client_secret

    await settings_service.set_many(updates)
    return RedirectResponse("/admin/settings?saved=1", status_code=302)


@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    user = await _require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    from app.api.users import USERS
    return templates.TemplateResponse(request=request, name="web/admin_users.html", context={
        "user": user,
        "users": list(USERS.values()),
    })


@router.post("/users/{user_id}/credits")
async def grant_credits(request: Request, user_id: str, amount: int = Form(...)):
    user = await _require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    from app.api.users import USERS
    if user_id in USERS:
        USERS[user_id]["credit_balance"] = USERS[user_id].get("credit_balance", 0) + amount
    return RedirectResponse("/admin/users", status_code=302)
