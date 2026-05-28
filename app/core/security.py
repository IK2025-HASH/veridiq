# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — Security Service
# Handles: 2FA (TOTP), email verification, password reset, session management

import uuid
import pyotp
import secrets
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory stores — replace with DB in production
EMAIL_TOKENS: dict[str, dict] = {}    # token -> {user_id, type, expires_at, used}
SESSIONS: dict[str, dict] = {}        # session_id -> {user_id, ip, ua, created, last_seen, active}
TOTP_SECRETS: dict[str, str] = {}     # user_id -> totp_secret
TWO_FA_PENDING: dict[str, str] = {}   # temp_token -> user_id (awaiting 2FA verification)


# ── EMAIL VERIFICATION ────────────────────────────────────────────────────────

def create_email_token(user_id: str, token_type: str, expires_hours: int = 24) -> str:
    """Generate a secure token for email verification or password reset."""
    token = secrets.token_urlsafe(32)
    EMAIL_TOKENS[token] = {
        "user_id": user_id,
        "type": token_type,          # verify_email | reset_password
        "expires_at": (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
        "used": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    return token


def verify_email_token(token: str, expected_type: str) -> str | None:
    """
    Validate a token. Returns user_id if valid, None otherwise.
    Marks token as used on success.
    """
    entry = EMAIL_TOKENS.get(token)
    if not entry:
        return None
    if entry["used"]:
        return None
    if entry["type"] != expected_type:
        return None
    if datetime.fromisoformat(entry["expires_at"]) < datetime.utcnow():
        return None
    entry["used"] = True
    return entry["user_id"]


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send a transactional email. Returns True on success."""
    if not settings.SMTP_USER:
        # Dev mode — log instead of sending
        logger.info(f"[DEV EMAIL] To: {to} | Subject: {subject}")
        logger.info(f"[DEV EMAIL] Body preview: {html_body[:200]}")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return False


def send_verification_email(user_id: str, email: str, name: str) -> bool:
    token = create_email_token(user_id, "verify_email", expires_hours=48)
    link = f"{settings.BASE_URL}/auth/verify-email/{token}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;background:#0D1B3E;color:#e2e8f0;padding:32px;border-radius:12px">
      <h1 style="color:#00B5AD;font-size:22px;margin-bottom:8px">Verid-iq</h1>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:24px">AI-Powered Test Intelligence · Network Logic</p>
      <h2 style="font-size:18px;color:#fff;margin-bottom:16px">Verify your email, {name}</h2>
      <p style="font-size:14px;color:#94a3b8;margin-bottom:24px">Click the button below to verify your email address and activate your account.</p>
      <a href="{link}" style="display:inline-block;background:#00B5AD;color:#0D1B3E;font-weight:bold;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:14px">Verify Email →</a>
      <p style="font-size:12px;color:#475569;margin-top:24px">Link expires in 48 hours. If you didn't create this account, ignore this email.</p>
    </div>"""
    return send_email(email, "Verify your Verid-iq email", html)


def send_password_reset_email(user_id: str, email: str, name: str) -> bool:
    token = create_email_token(user_id, "reset_password", expires_hours=1)
    link = f"{settings.BASE_URL}/auth/reset-password/{token}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;background:#0D1B3E;color:#e2e8f0;padding:32px;border-radius:12px">
      <h1 style="color:#00B5AD;font-size:22px;margin-bottom:8px">Verid-iq</h1>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:24px">AI-Powered Test Intelligence · Network Logic</p>
      <h2 style="font-size:18px;color:#fff;margin-bottom:16px">Reset your password</h2>
      <p style="font-size:14px;color:#94a3b8;margin-bottom:24px">Hi {name}, you requested a password reset. This link expires in 1 hour.</p>
      <a href="{link}" style="display:inline-block;background:#00B5AD;color:#0D1B3E;font-weight:bold;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:14px">Reset Password →</a>
      <p style="font-size:12px;color:#475569;margin-top:24px">If you didn't request this, your password is safe — ignore this email.</p>
    </div>"""
    return send_email(email, "Reset your Verid-iq password", html)


# ── SESSION MANAGEMENT ────────────────────────────────────────────────────────

def create_session(user_id: str, ip: str, user_agent: str) -> str:
    session_id = secrets.token_urlsafe(40)
    SESSIONS[session_id] = {
        "id": session_id,
        "user_id": user_id,
        "ip": ip,
        "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "active": True,
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    s = SESSIONS.get(session_id)
    if s and s["active"]:
        s["last_seen"] = datetime.utcnow().isoformat()
        return s
    return None


def revoke_session(session_id: str) -> None:
    if session_id in SESSIONS:
        SESSIONS[session_id]["active"] = False


def revoke_all_sessions(user_id: str, except_session: str | None = None) -> int:
    count = 0
    for sid, s in SESSIONS.items():
        if s["user_id"] == user_id and s["active"] and sid != except_session:
            s["active"] = False
            count += 1
    return count


def get_user_sessions(user_id: str) -> list[dict]:
    return [
        {k: v for k, v in s.items() if k != "user_id"}
        for s in SESSIONS.values()
        if s["user_id"] == user_id and s["active"]
    ]


# ── TOTP / 2FA ────────────────────────────────────────────────────────────────

def setup_totp(user_id: str, display_name: str) -> dict:
    """Generate a new TOTP secret and return QR code URI."""
    secret = pyotp.random_base32()
    TOTP_SECRETS[user_id] = secret
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=display_name,
        issuer_name="Verid-iq by Network Logic"
    )
    return {"secret": secret, "uri": uri}


def verify_totp(user_id: str, code: str) -> bool:
    """Verify a TOTP code for a user."""
    secret = TOTP_SECRETS.get(user_id)
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def get_totp_enabled(user_id: str) -> bool:
    return user_id in TOTP_SECRETS


def disable_totp(user_id: str) -> None:
    TOTP_SECRETS.pop(user_id, None)


def create_2fa_pending_token(user_id: str) -> str:
    """After password check passes, hold user here until 2FA is confirmed."""
    token = secrets.token_urlsafe(24)
    TWO_FA_PENDING[token] = user_id
    return token


def consume_2fa_pending_token(token: str) -> str | None:
    return TWO_FA_PENDING.pop(token, None)
