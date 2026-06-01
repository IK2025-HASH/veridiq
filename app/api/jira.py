# Copyright © 2026 Network Logic Limited. All rights reserved.

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.core.jira_client import JiraClient
from app.api.users import get_current_user, require_user

logger = logging.getLogger(__name__)
router = APIRouter()


class JiraConnectRequest(BaseModel):
    jira_url: str = Field(..., description="e.g. https://yourcompany.atlassian.net")
    jira_email: str
    api_token: str


class PushXrayRequest(BaseModel):
    project_key: str
    summary: str
    content: str
    linked_issue_key: Optional[str] = None


def _jira_error(exc: Exception) -> HTTPException:
    msg = str(exc)
    if isinstance(exc, PermissionError) or "401" in msg or "Unauthorized" in msg:
        return HTTPException(401, "Invalid Jira credentials — check your email and API token")
    if any(x in msg for x in ("ConnectError", "ConnectTimeout", "getaddrinfo", "Name or service")):
        return HTTPException(400, "Cannot reach Jira — check the URL is correct")
    if "404" in msg:
        return HTTPException(404, msg)
    return HTTPException(400, f"Jira error: {msg}")


@router.post("/jira/connect")
async def connect_jira(request: Request, body: JiraConnectRequest):
    user = require_user(request)
    client = JiraClient(body.jira_url, body.jira_email, body.api_token)
    try:
        result = await client.test_connection()
    except Exception as e:
        raise _jira_error(e)

    user["jira_url"] = body.jira_url.rstrip("/")
    user["jira_email"] = body.jira_email
    user["jira_api_token"] = body.api_token
    user["jira_display_name"] = result.get("display_name", "")

    # Persist so credentials survive server restarts
    from app.core import settings_service
    await settings_service.set_many({
        f"jira_url__{user['id']}":          user["jira_url"],
        f"jira_email__{user['id']}":         user["jira_email"],
        f"jira_api_token__{user['id']}":     user["jira_api_token"],
        f"jira_display_name__{user['id']}":  user["jira_display_name"],
    })

    return {"ok": True, "display_name": result.get("display_name", "")}


@router.post("/jira/disconnect")
async def disconnect_jira(request: Request):
    user = require_user(request)
    for key in ("jira_url", "jira_email", "jira_api_token", "jira_display_name"):
        user.pop(key, None)

    from app.core import settings_service
    await settings_service.set_many({
        f"jira_url__{user['id']}":         "",
        f"jira_email__{user['id']}":        "",
        f"jira_api_token__{user['id']}":    "",
        f"jira_display_name__{user['id']}": "",
    })
    return {"ok": True}


@router.get("/jira/status")
async def jira_status(request: Request):
    user = get_current_user(request)
    if not user or not user.get("jira_url"):
        return {"connected": False}
    return {
        "connected": True,
        "jira_url": user["jira_url"],
        "display_name": user.get("jira_display_name", ""),
    }


@router.get("/jira/projects")
async def list_jira_projects(request: Request):
    user = require_user(request)
    if not user.get("jira_url"):
        raise HTTPException(400, "Jira not connected — set up in Profile → Jira Connection")
    client = JiraClient(user["jira_url"], user["jira_email"], user["jira_api_token"])
    try:
        projects = await client.list_projects()
        return {"projects": projects}
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except Exception as e:
        logger.error(f"Jira projects error: {e}")
        raise _jira_error(e)


@router.get("/jira/projects/{project_key}/issues")
async def list_project_issues(request: Request, project_key: str):
    user = require_user(request)
    if not user.get("jira_url"):
        raise HTTPException(400, "Jira not connected — set up in Profile → Jira Connection")
    client = JiraClient(user["jira_url"], user["jira_email"], user["jira_api_token"])
    try:
        issues = await client.search_issues(project_key.upper())
        return {"issues": issues}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except Exception as e:
        logger.error(f"Jira issue search error: {e}")
        raise _jira_error(e)


@router.get("/jira/issue/{issue_key}")
async def get_jira_issue(request: Request, issue_key: str):
    user = require_user(request)
    if not user.get("jira_url"):
        raise HTTPException(400, "Jira not connected — set up in Profile → Jira Connection")
    client = JiraClient(user["jira_url"], user["jira_email"], user["jira_api_token"])
    try:
        return await client.get_issue(issue_key.upper())
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except Exception as e:
        logger.error(f"Jira fetch error: {e}")
        raise _jira_error(e)


@router.post("/jira/push-xray")
async def push_to_xray(request: Request, body: PushXrayRequest):
    user = require_user(request)
    if not user.get("jira_url"):
        raise HTTPException(400, "Jira not connected — set up in Profile → Jira Connection")
    client = JiraClient(user["jira_url"], user["jira_email"], user["jira_api_token"])
    try:
        return await client.create_xray_test(
            project_key=body.project_key.upper(),
            summary=body.summary,
            content=body.content,
            linked_issue_key=body.linked_issue_key or None,
        )
    except Exception as e:
        logger.error(f"Xray push error: {e}")
        raise _jira_error(e)
