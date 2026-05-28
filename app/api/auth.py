# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — Full Authentication Routes
# Covers: email registration, LinkedIn OAuth, email verification,
#         password reset, 2FA setup/verify, session management

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import (
    hash_password, verify_password,
    create_access_token, decode_token,
)
from app.core.security import (
    send_verification_email, send_password_reset_email,
    verify_email_token, create_session, get_session,
    revoke_session, revoke_all_sessions, get_user_sessions,
    setup_totp, verify_totp, get_totp_enabled, disable_totp,
    create_2fa_pending_token, consume_2fa_pending_token,
)
from app.core.linkedin_oauth import (
    get_linkedin_auth_url, validate_state,
    exchange_code_for_token, get_linkedin_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Shared user store (wired to DB in production)
from app.api.users import USERS, CREDIT_TXNS, TOPUP_PACKS, TIER_LABELS

LINKEDIN_ACCOUNTS: dict[str, str] = {}  # linkedin_id -> user_id


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _make_user(user_id: str, email: str, display_name: str,
               hashed_pw: str | None, avatar_url: str | None,
               account_type: str = "individual",
               via_linkedin: bool = False) -> dict:
    user = {
        "id": user_id,
        "email": email,
        "hashed_password": hashed_pw or "",
        "display_name": display_name,
        "avatar_url": avatar_url,
        "account_type": account_type,
        "tier": "free",
        "credit_balance": 50,
        "credits_used_month": 0,
        "credits_used_total": 0,
        "team_id": None,
        "team_role": None,
        "email_verified": via_linkedin,   # LinkedIn emails are pre-verified
        "is_active": True,
        "is_admin": False,
        "classified_mode": False,
        "billing_name": display_name,
        "billing_address": None,
        "billing_vat": None,
        "company_name": None,
        "phone": None,
        "two_fa_enabled": False,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
    }
    USERS[user_id] = user
    CREDIT_TXNS.append({
        "user_id": user_id, "amount": 50, "txn_type": "signup",
        "description": "Welcome credits", "balance_after": 50,
        "created_at": datetime.utcnow().isoformat()
    })
    return user


def _set_auth_cookie(response: Response, user_id: str, email: str,
                     request: Request | None = None) -> str:
    token = create_access_token(user_id, email)
    response.set_cookie(
        "access_token", token,
        httponly=True, samesite="lax",
        secure=True, max_age=86400
    )
    if request:
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "")
        create_session(user_id, ip, ua)
    return token


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return USERS.get(payload.get("sub"))


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=100)
    account_type: str = "individual"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

class TwoFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)

class TwoFAEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


# ── REGISTER ──────────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request=request, name="web/register.html", context={
        "linkedin_enabled": bool(settings.LINKEDIN_CLIENT_ID)
    })


@router.post("/api/auth/register")
async def register(body: RegisterRequest, request: Request, response: Response):
    if any(u["email"] == body.email for u in USERS.values()):
        raise HTTPException(400, "An account with this email already exists")

    user_id = str(uuid.uuid4())
    user = _make_user(
        user_id, body.email, body.display_name,
        hash_password(body.password), None, body.account_type
    )

    # Send verification email (non-blocking)
    send_verification_email(user_id, body.email, body.display_name)

    _set_auth_cookie(response, user_id, body.email, request)
    return {"ok": True, "redirect": "/auth/verify-email-sent"}


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request=request, name="web/login.html", context={
        "linkedin_enabled": bool(settings.LINKEDIN_CLIENT_ID)
    })


@router.post("/api/auth/login")
async def login(body: LoginRequest, request: Request, response: Response):
    user = next((u for u in USERS.values() if u["email"] == body.email), None)
    if not user or not user.get("hashed_password"):
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    if not user["is_active"]:
        raise HTTPException(403, "Account suspended — contact support")

    # 2FA gate
    if user.get("two_fa_enabled"):
        pending_token = create_2fa_pending_token(user["id"])
        return {"ok": True, "requires_2fa": True, "pending_token": pending_token}

    user["last_login"] = datetime.utcnow().isoformat()
    _set_auth_cookie(response, user["id"], user["email"], request)
    return {"ok": True, "redirect": "/dashboard"}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            # Revoke session
            for sid, s in list(get_user_sessions(payload.get("sub", "")).__class__.__mro__):
                pass  # sessions handled by security module
    response.delete_cookie("access_token")
    return {"ok": True}


# ── LINKEDIN OAUTH ────────────────────────────────────────────────────────────

@router.get("/auth/linkedin")
async def linkedin_start():
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(503, "LinkedIn login not configured")
    url, state = get_linkedin_auth_url()
    response = RedirectResponse(url)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/auth/linkedin/callback")
async def linkedin_callback(request: Request, response: Response,
                             code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/login?error=linkedin_{error}")

    saved_state = request.cookies.get("oauth_state")
    if not saved_state or saved_state != state or not validate_state(state):
        return RedirectResponse("/login?error=oauth_state_mismatch")

    access_token = await exchange_code_for_token(code)
    if not access_token:
        return RedirectResponse("/login?error=oauth_token_failed")

    profile = await get_linkedin_profile(access_token)
    if not profile or not profile.get("email"):
        return RedirectResponse("/login?error=oauth_profile_failed")

    linkedin_id = profile["linkedin_id"]
    email = profile["email"]
    name = profile["name"]
    avatar = profile.get("avatar_url")

    # Find or create user
    existing_user_id = LINKEDIN_ACCOUNTS.get(linkedin_id)
    if existing_user_id:
        user = USERS.get(existing_user_id)
    else:
        # Check if email already registered
        user = next((u for u in USERS.values() if u["email"] == email), None)
        if user:
            # Link LinkedIn to existing account
            LINKEDIN_ACCOUNTS[linkedin_id] = user["id"]
            user["email_verified"] = True
            if not user.get("avatar_url") and avatar:
                user["avatar_url"] = avatar
        else:
            # New user via LinkedIn
            user_id = str(uuid.uuid4())
            user = _make_user(user_id, email, name, None, avatar, via_linkedin=True)
            LINKEDIN_ACCOUNTS[linkedin_id] = user_id

    if not user or not user["is_active"]:
        return RedirectResponse("/login?error=account_suspended")

    user["last_login"] = datetime.utcnow().isoformat()
    resp = RedirectResponse("/dashboard")
    _set_auth_cookie(resp, user["id"], user["email"], request)
    resp.delete_cookie("oauth_state")
    return resp


# ── EMAIL VERIFICATION ────────────────────────────────────────────────────────

@router.get("/auth/verify-email-sent", response_class=HTMLResponse)
async def verify_email_sent(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="web/verify_email_sent.html",
        context={"user": user})


@router.get("/auth/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    user_id = verify_email_token(token, "verify_email")
    if not user_id:
        return templates.TemplateResponse(request=request, name="web/auth_message.html",
            context={"title": "Link expired", "message": "This verification link has expired or already been used.", "action_href": "/login", "action_label": "Sign in"})
    user = USERS.get(user_id)
    if user:
        user["email_verified"] = True
    return templates.TemplateResponse(request=request, name="web/auth_message.html",
        context={"title": "Email verified ✓", "message": "Your email address has been verified. You're all set.", "action_href": "/dashboard", "action_label": "Go to dashboard"})


@router.post("/api/auth/resend-verification")
async def resend_verification(request: Request):
    user = require_user(request)
    if user.get("email_verified"):
        return {"ok": True, "message": "Already verified"}
    send_verification_email(user["id"], user["email"], user["display_name"])
    return {"ok": True}


# ── PASSWORD RESET ────────────────────────────────────────────────────────────

@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="web/forgot_password.html", context={})


@router.post("/api/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    user = next((u for u in USERS.values() if u["email"] == body.email), None)
    # Always return success to prevent email enumeration
    if user and user["is_active"]:
        send_password_reset_email(user["id"], user["email"], user["display_name"])
    return {"ok": True, "message": "If an account exists, a reset link has been sent"}


@router.get("/auth/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse(request=request, name="web/reset_password.html",
        context={"token": token})


@router.post("/api/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    user_id = verify_email_token(body.token, "reset_password")
    if not user_id:
        raise HTTPException(400, "Reset link is invalid or has expired")
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(404, "Account not found")
    user["hashed_password"] = hash_password(body.new_password)
    # Revoke all sessions after password reset
    revoke_all_sessions(user_id)
    return {"ok": True, "redirect": "/login?message=password_reset"}


@router.post("/api/auth/change-password")
async def change_password(request: Request, body: ChangePasswordRequest, response: Response):
    user = require_user(request)
    if not user.get("hashed_password"):
        raise HTTPException(400, "Password change not available for social login accounts")
    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(400, "Current password is incorrect")
    user["hashed_password"] = hash_password(body.new_password)
    revoke_all_sessions(user["id"])
    response.delete_cookie("access_token")
    return {"ok": True, "redirect": "/login?message=password_changed"}


# ── TWO-FACTOR AUTHENTICATION ─────────────────────────────────────────────────

@router.get("/auth/2fa/setup", response_class=HTMLResponse)
async def two_fa_setup_page(request: Request):
    user = require_user(request)
    totp_data = setup_totp(user["id"], user["display_name"])
    return templates.TemplateResponse(request=request, name="web/two_fa_setup.html", context={
        "user": user,
        "totp_uri": totp_data["uri"],
        "totp_secret": totp_data["secret"],
        "two_fa_enabled": get_totp_enabled(user["id"]) and user.get("two_fa_enabled"),
    })


@router.post("/api/auth/2fa/enable")
async def enable_two_fa(request: Request, body: TwoFAEnableRequest):
    user = require_user(request)
    if not verify_totp(user["id"], body.code):
        raise HTTPException(400, "Invalid code — check your authenticator app and try again")
    user["two_fa_enabled"] = True
    return {"ok": True, "message": "Two-factor authentication enabled"}


@router.post("/api/auth/2fa/disable")
async def disable_two_fa(request: Request, body: TwoFAVerifyRequest):
    user = require_user(request)
    if not verify_totp(user["id"], body.code):
        raise HTTPException(400, "Invalid code")
    disable_totp(user["id"])
    user["two_fa_enabled"] = False
    return {"ok": True}


@router.post("/api/auth/2fa/verify")
async def verify_two_fa(body: dict, response: Response, request: Request):
    """Called after password login when 2FA is required."""
    pending_token = body.get("pending_token")
    code = body.get("code", "")
    user_id = consume_2fa_pending_token(pending_token)
    if not user_id:
        raise HTTPException(400, "Session expired — please sign in again")
    if not verify_totp(user_id, code):
        raise HTTPException(400, "Invalid 2FA code")
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(404)
    user["last_login"] = datetime.utcnow().isoformat()
    _set_auth_cookie(response, user_id, user["email"], request)
    return {"ok": True, "redirect": "/dashboard"}


# ── SESSION MANAGEMENT ────────────────────────────────────────────────────────

@router.get("/security", response_class=HTMLResponse)
async def security_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    sessions = get_user_sessions(user["id"])
    current_token = request.cookies.get("access_token", "")
    return templates.TemplateResponse(request=request, name="web/security.html", context={
        "user": user,
        "sessions": sessions,
        "two_fa_enabled": get_totp_enabled(user["id"]) and user.get("two_fa_enabled"),
        "has_linkedin": any(uid == user["id"] for uid in LINKEDIN_ACCOUNTS.values()),
        "has_password": bool(user.get("hashed_password")),
    })


@router.post("/api/auth/sessions/{session_id}/revoke")
async def revoke_session_endpoint(request: Request, session_id: str):
    user = require_user(request)
    session = get_session(session_id)
    if not session or session.get("user_id") != user["id"]:
        raise HTTPException(404, "Session not found")
    revoke_session(session_id)
    return {"ok": True}


@router.post("/api/auth/sessions/revoke-all")
async def revoke_all_sessions_endpoint(request: Request, response: Response):
    user = require_user(request)
    current_token = request.cookies.get("access_token", "")
    revoke_all_sessions(user["id"])
    response.delete_cookie("access_token")
    return {"ok": True, "redirect": "/login"}
