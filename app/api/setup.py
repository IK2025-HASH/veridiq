# Copyright © 2026 Network Logic Limited. All rights reserved.
# First-boot setup wizard — runs once, stores config in DB.

import uuid
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core import settings_service
from app.core.auth import hash_password, create_access_token
from app.core.security import create_session

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    try:
        if await settings_service.is_setup_complete():
            return RedirectResponse("/", status_code=302)
    except Exception:
        pass
    return templates.TemplateResponse(request=request, name="web/setup.html", context={"error": None})


@router.post("/setup")
async def setup_submit(
    request: Request,
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    anthropic_api_key: str = Form(...),
    smtp_host: str = Form(default=""),
    smtp_user: str = Form(default=""),
    smtp_password: str = Form(default=""),
):
    if await settings_service.is_setup_complete():
        return RedirectResponse("/", status_code=302)

    errors = []
    if len(admin_password) < 8:
        errors.append("Password must be at least 8 characters")
    if not anthropic_api_key.strip().startswith("sk-ant-"):
        errors.append("Invalid Anthropic API key — must start with sk-ant-")

    if errors:
        return templates.TemplateResponse(
            request=request, name="web/setup.html",
            context={"error": " · ".join(errors)}, status_code=400,
        )

    # Create admin user in the in-memory store
    from app.api.users import USERS
    admin_id = str(uuid.uuid4())
    admin_hashed_pw = hash_password(admin_password)
    USERS[admin_id] = {
        "id": admin_id,
        "email": admin_email,
        "display_name": "Admin",
        "hashed_password": admin_hashed_pw,
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
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        "last_login": None,
    }

    # Persist settings to DB (including admin credentials for restart recovery)
    data: dict[str, str] = {
        "admin_email": admin_email,
        "admin_id": admin_id,
        "admin_password_hash": admin_hashed_pw,
        "anthropic_api_key": anthropic_api_key.strip(),
        "setup_complete": "true",
    }
    if smtp_host:
        data["smtp_host"] = smtp_host
    if smtp_user:
        data["smtp_user"] = smtp_user
    if smtp_password:
        data["smtp_password"] = smtp_password

    await settings_service.set_many(data)
    request.app.state.setup_complete = True

    # Log the admin in
    token = create_access_token(admin_id, admin_email)
    ip = str(request.client.host) if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    session_id = create_session(admin_id, ip, user_agent)

    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response
