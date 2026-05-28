# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — User, Team, Credit & Invoice API Routes

import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# ── In-memory store (replace with DB queries in production) ──────────────────
# These functions are stubs — wire to SQLAlchemy async sessions for production

USERS: dict[str, dict] = {}
TEAMS: dict[str, dict] = {}
INVITES: dict[str, dict] = {}
CREDIT_TXNS: list[dict] = []
INVOICES: list[dict] = []
INVOICE_COUNTER = [1000]

TIER_CREDITS = {
    "free":       50,
    "starter":    300,
    "team":       1000,
    "growth":     3000,
    "enterprise": 999999,
}

TIER_LABELS = {
    "free":       "Free",
    "starter":    "Starter",
    "team":       "Team",
    "growth":     "Growth",
    "enterprise": "Enterprise",
}


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    return USERS.get(user_id)


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def next_invoice_number() -> str:
    INVOICE_COUNTER[0] += 1
    return f"VIQ-{datetime.utcnow().year}-{INVOICE_COUNTER[0]:05d}"


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=100)
    account_type: str = "individual"  # individual | team_owner

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    billing_name: str | None = None
    billing_address: str | None = None
    billing_vat: str | None = None
    classified_mode: bool | None = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None

class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"

class CreditTopupRequest(BaseModel):
    pack: str  # small|medium|large

TOPUP_PACKS = {
    "small":  {"credits": 100,  "net_pence": 500,  "label": "100 credits — £5.00"},
    "medium": {"credits": 500,  "net_pence": 2000, "label": "500 credits — £20.00"},
    "large":  {"credits": 2000, "net_pence": 6500, "label": "2,000 credits — £65.00"},
}


# ── AUTH ROUTES ───────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="web/register.html")

@router.post("/api/auth/register")
async def register(body: RegisterRequest, response: Response):
    if any(u["email"] == body.email for u in USERS.values()):
        raise HTTPException(400, "Email already registered")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "display_name": body.display_name,
        "account_type": body.account_type,
        "tier": "free",
        "credit_balance": 50,
        "credits_used_month": 0,
        "credits_used_total": 0,
        "team_id": None,
        "team_role": None,
        "email_verified": False,
        "is_active": True,
        "is_admin": False,
        "classified_mode": False,
        "billing_name": body.display_name,
        "billing_address": None,
        "billing_vat": None,
        "company_name": None,
        "phone": None,
        "avatar_url": None,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
    }
    USERS[user_id] = user

    # Grant signup credits
    CREDIT_TXNS.append({
        "user_id": user_id, "amount": 50, "txn_type": "signup",
        "description": "Welcome credits", "balance_after": 50,
        "created_at": datetime.utcnow().isoformat()
    })

    token = create_access_token(user_id, body.email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400)
    return {"ok": True, "redirect": "/dashboard"}

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="web/login.html")

@router.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    user = next((u for u in USERS.values() if u["email"] == body.email), None)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    if not user["is_active"]:
        raise HTTPException(403, "Account suspended")

    user["last_login"] = datetime.utcnow().isoformat()
    token = create_access_token(user["id"], user["email"])
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400)
    return {"ok": True, "redirect": "/dashboard"}

@router.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}

@router.post("/api/auth/change-password")
async def change_password(request: Request, body: PasswordChangeRequest):
    user = require_user(request)
    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(400, "Current password is incorrect")
    user["hashed_password"] = hash_password(body.new_password)
    return {"ok": True}


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    txns = [t for t in CREDIT_TXNS if t["user_id"] == user["id"]][-10:]
    return templates.TemplateResponse(request=request, name="web/dashboard.html",
        context={"user": user, "recent_txns": txns[::-1]})


# ── PROFILE ROUTES ────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(request=request, name="web/profile.html", context={"user": user})

@router.post("/api/user/profile")
async def update_profile(request: Request, body: ProfileUpdateRequest):
    user = require_user(request)
    for field, val in body.model_dump(exclude_none=True).items():
        user[field] = val
    return {"ok": True, "user": {k: v for k, v in user.items() if k != "hashed_password"}}

@router.delete("/api/user/account")
async def delete_account(request: Request):
    user = require_user(request)
    user["is_active"] = False
    user["email"] = f"deleted_{user['id']}@deleted.invalid"
    return {"ok": True}


# ── TEAM ROUTES ───────────────────────────────────────────────────────────────

@router.get("/team", response_class=HTMLResponse)
async def team_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    team = TEAMS.get(user.get("team_id")) if user.get("team_id") else None
    team_members = [u for u in USERS.values() if u.get("team_id") == user.get("team_id")] if team else []
    pending_invites = [i for i in INVITES.values() if i.get("team_id") == user.get("team_id") and not i["accepted"]] if team else []
    return templates.TemplateResponse(request=request, name="web/team.html",
        context={"user": user, "team": team, "members": team_members, "invites": pending_invites})

@router.post("/api/team/create")
async def create_team(request: Request, body: TeamCreateRequest):
    user = require_user(request)
    if user.get("team_id"):
        raise HTTPException(400, "Already in a team")

    team_id = str(uuid.uuid4())
    slug = body.name.lower().replace(" ", "-")[:50]
    team = {
        "id": team_id, "name": body.name, "slug": slug,
        "description": body.description, "owner_id": user["id"],
        "tier": "team", "shared_credit_pool": 1000, "credits_used_month": 0,
        "classified_mode": False, "max_members": 10,
        "created_at": datetime.utcnow().isoformat()
    }
    TEAMS[team_id] = team
    user["team_id"] = team_id
    user["team_role"] = "owner"
    user["account_type"] = "team_owner"
    user["tier"] = "team"
    user["credit_balance"] = 1000
    return {"ok": True, "team": team}

@router.post("/api/team/invite")
async def invite_member(request: Request, body: InviteRequest):
    user = require_user(request)
    if user.get("team_role") not in ("owner", "admin"):
        raise HTTPException(403, "Only team owners and admins can invite members")

    invite_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    invite = {
        "id": invite_id, "team_id": user["team_id"],
        "email": body.email, "role": body.role,
        "token": token, "accepted": False,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    INVITES[invite_id] = invite
    # In production: send invite email with link /join/{token}
    return {"ok": True, "invite_link": f"/join/{token}"}

@router.get("/join/{token}", response_class=HTMLResponse)
async def join_team(request: Request, token: str):
    invite = next((i for i in INVITES.values() if i["token"] == token), None)
    if not invite or invite["accepted"]:
        return HTMLResponse("<h1>Invalid or expired invite link.</h1>", status_code=400)
    team = TEAMS.get(invite["team_id"])
    return templates.TemplateResponse(request=request, name="web/join_team.html",
        context={"invite": invite, "team": team})

@router.post("/api/team/remove-member/{member_id}")
async def remove_member(request: Request, member_id: str):
    user = require_user(request)
    if user.get("team_role") not in ("owner", "admin"):
        raise HTTPException(403, "Insufficient permissions")
    member = USERS.get(member_id)
    if not member or member.get("team_id") != user.get("team_id"):
        raise HTTPException(404, "Member not found")
    if member["id"] == TEAMS[user["team_id"]]["owner_id"]:
        raise HTTPException(400, "Cannot remove team owner")
    member["team_id"] = None
    member["team_role"] = None
    member["account_type"] = "individual"
    return {"ok": True}

@router.post("/api/team/update-role/{member_id}")
async def update_role(request: Request, member_id: str, role: str):
    user = require_user(request)
    if user.get("team_role") != "owner":
        raise HTTPException(403, "Only team owner can change roles")
    member = USERS.get(member_id)
    if not member:
        raise HTTPException(404, "Member not found")
    member["team_role"] = role
    return {"ok": True}


# ── CREDIT ROUTES ─────────────────────────────────────────────────────────────

@router.get("/credits", response_class=HTMLResponse)
async def credits_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    txns = [t for t in CREDIT_TXNS if t["user_id"] == user["id"]]
    return templates.TemplateResponse(request=request, name="web/credits.html",
        context={"user": user, "transactions": txns[::-1], "packs": TOPUP_PACKS,
                 "tier_credits": TIER_CREDITS, "tier_labels": TIER_LABELS})

@router.post("/api/credits/topup")
async def topup_credits(request: Request, body: CreditTopupRequest):
    user = require_user(request)
    pack = TOPUP_PACKS.get(body.pack)
    if not pack:
        raise HTTPException(400, "Invalid pack")

    # In production: Stripe payment intent → confirm → then credit
    # For soft launch: direct credit (demo mode)
    credits = pack["credits"]
    net = pack["net_pence"]
    vat = int(net * 0.20)
    gross = net + vat

    user["credit_balance"] += credits
    user["credits_used_total"] = user.get("credits_used_total", 0)

    inv_number = next_invoice_number()
    invoice = {
        "id": str(uuid.uuid4()),
        "invoice_number": inv_number,
        "user_id": user["id"],
        "billing_name": user.get("billing_name") or user["display_name"],
        "billing_address": user.get("billing_address"),
        "billing_vat": user.get("billing_vat"),
        "company_name": user.get("company_name"),
        "description": pack["label"],
        "credits_purchased": credits,
        "amount_net": net,
        "vat_rate": 20,
        "vat_amount": vat,
        "amount_gross": gross,
        "status": "paid",
        "invoice_date": datetime.utcnow().isoformat(),
    }
    INVOICES.append(invoice)

    CREDIT_TXNS.append({
        "user_id": user["id"], "amount": credits, "txn_type": "topup",
        "description": pack["label"], "balance_after": user["credit_balance"],
        "invoice_id": invoice["id"], "created_at": datetime.utcnow().isoformat()
    })

    return {"ok": True, "new_balance": user["credit_balance"], "invoice_number": inv_number}

@router.get("/api/credits/balance")
async def get_balance(request: Request):
    user = get_current_user(request)
    if not user:
        return {"balance": 50, "tier": "free"}
    return {
        "balance": user["credit_balance"],
        "tier": user["tier"],
        "tier_label": TIER_LABELS.get(user["tier"], "Free"),
        "used_today": 0,  # wire to daily aggregate query in production
        "used_month": user.get("credits_used_month", 0),
    }


# ── INVOICE ROUTES ────────────────────────────────────────────────────────────

@router.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    user_invoices = [i for i in INVOICES if i["user_id"] == user["id"]]
    return templates.TemplateResponse(request=request, name="web/invoices.html",
        context={"user": user, "invoices": user_invoices[::-1]})

@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
async def invoice_detail(request: Request, invoice_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    invoice = next((i for i in INVOICES if i["id"] == invoice_id and i["user_id"] == user["id"]), None)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return templates.TemplateResponse(request=request, name="web/invoice_print.html",
        context={"user": user, "invoice": invoice})


# ── ADMIN ROUTES ──────────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    return templates.TemplateResponse(request=request, name="web/admin.html",
        context={
            "user": user,
            "all_users": list(USERS.values()),
            "all_teams": list(TEAMS.values()),
            "total_credits_issued": sum(t["amount"] for t in CREDIT_TXNS if t["amount"] > 0),
            "total_generations": sum(1 for t in CREDIT_TXNS if t.get("txn_type") == "generation"),
        })

@router.post("/api/admin/grant-credits")
async def admin_grant_credits(request: Request, user_id: str, amount: int, reason: str = "admin grant"):
    admin = require_user(request)
    if not admin.get("is_admin"):
        raise HTTPException(403)
    target = USERS.get(user_id)
    if not target:
        raise HTTPException(404)
    target["credit_balance"] += amount
    CREDIT_TXNS.append({
        "user_id": user_id, "amount": amount, "txn_type": "admin_grant",
        "description": reason, "balance_after": target["credit_balance"],
        "created_at": datetime.utcnow().isoformat()
    })
    return {"ok": True, "new_balance": target["credit_balance"]}
