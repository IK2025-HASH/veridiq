# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — LinkedIn OAuth 2.0 Integration

import httpx
import secrets
import logging
from app.config import settings

logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL  = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"  # OpenID Connect endpoint

SCOPES = "openid profile email"

# In-memory CSRF state store — replace with Redis/DB in production
OAUTH_STATES: dict[str, str] = {}  # state -> "linkedin"


def get_linkedin_auth_url() -> tuple[str, str]:
    """
    Build the LinkedIn OAuth authorisation URL.
    Returns (url, state) — store state in session to verify on callback.
    """
    state = secrets.token_urlsafe(16)
    OAUTH_STATES[state] = "linkedin"

    params = (
        f"response_type=code"
        f"&client_id={settings.LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&state={state}"
    )
    return f"{LINKEDIN_AUTH_URL}?{params}", state


def validate_state(state: str) -> bool:
    return OAUTH_STATES.pop(state, None) == "linkedin"


async def exchange_code_for_token(code: str) -> str | None:
    """Exchange the authorisation code for an access token."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(LINKEDIN_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            r.raise_for_status()
            return r.json().get("access_token")
        except Exception as e:
            logger.error(f"LinkedIn token exchange failed: {e}")
            return None


async def get_linkedin_profile(access_token: str) -> dict | None:
    """
    Fetch the user's LinkedIn profile using OpenID Connect userinfo endpoint.
    Returns: {sub, email, name, given_name, family_name, picture}
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                LINKEDIN_PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            r.raise_for_status()
            profile = r.json()
            return {
                "linkedin_id": profile.get("sub"),
                "email": profile.get("email"),
                "name": profile.get("name") or f"{profile.get('given_name','')} {profile.get('family_name','')}".strip(),
                "avatar_url": profile.get("picture"),
            }
        except Exception as e:
            logger.error(f"LinkedIn profile fetch failed: {e}")
            return None
