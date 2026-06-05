# Copyright © 2026 Network Logic Limited. All rights reserved.

import re
import logging
import base64
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


XRAY_CLOUD_BASE = "https://xray.cloud.getxray.app/api/v2"


class JiraClient:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        xray_client_id: str = "",
        xray_client_secret: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.xray_client_id = xray_client_id
        self.xray_client_secret = xray_client_secret
        self._xray_token: Optional[str] = None
        encoded = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_xray_token(self, client: httpx.AsyncClient) -> Optional[str]:
        """Exchange Xray Cloud Client ID/Secret for a Bearer token (cached per instance)."""
        if self._xray_token:
            return self._xray_token
        if not self.xray_client_id or not self.xray_client_secret:
            return None
        try:
            r = await client.post(
                f"{XRAY_CLOUD_BASE}/authenticate",
                json={"client_id": self.xray_client_id, "client_secret": self.xray_client_secret},
                headers={"Content-Type": "application/json"},
                timeout=15.0,
            )
            if r.is_success:
                token = r.json()  # response is a quoted JWT string
                if isinstance(token, str) and token:
                    self._xray_token = token
                    logger.info("Xray Cloud v2 token obtained successfully")
                    return self._xray_token
            logger.warning(f"Xray auth failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            logger.warning(f"Xray auth exception: {e}")
        return None

    def _xray_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def test_connection(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.base_url}/rest/api/3/myself", headers=self._headers)
            r.raise_for_status()
            data = r.json()
            return {
                "ok": True,
                "display_name": data.get("displayName", ""),
                "email": data.get("emailAddress", ""),
            }

    async def list_projects(self) -> list[dict]:
        """Return all projects the connected user can see."""
        projects: list[dict] = []
        start = 0
        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                r = await client.get(
                    f"{self.base_url}/rest/api/3/project/search",
                    headers=self._headers,
                    params={"startAt": start, "maxResults": 50, "orderBy": "name"},
                )
                if r.status_code == 401:
                    raise PermissionError("Invalid Jira credentials")
                r.raise_for_status()
                data = r.json()
                for p in data.get("values", []):
                    projects.append({
                        "key": p.get("key", ""),
                        "name": p.get("name", ""),
                        "type": p.get("projectTypeKey", ""),
                    })
                if data.get("isLast", True):
                    break
                start += 50
        return projects

    async def search_issues(self, project_key: str, max_results: int = 50) -> list[dict]:
        """Return Story issues for a project (newest first).

        Filters to issuetype = Story so Test, Test Set, and other Xray
        issue types created by Verid-iq don't clutter the backlog view.
        Uses /rest/api/3/search/jql — the old /rest/api/3/search was
        deprecated by Atlassian and now returns 410 Gone.
        """
        jql = f'project = "{project_key}" AND issuetype = Story ORDER BY updated DESC'
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self.base_url}/rest/api/3/search/jql",
                headers=self._headers,
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "summary,issuetype,status",
                },
            )
            if r.status_code == 401:
                raise PermissionError("Invalid Jira credentials")
            if r.status_code == 400:
                raise ValueError(f"Could not search project {project_key}")
            r.raise_for_status()
            data = r.json()
            issues = []
            for it in data.get("issues", []):
                fields = it.get("fields", {})
                issues.append({
                    "key": it.get("key", ""),
                    "summary": fields.get("summary", ""),
                    "issue_type": fields.get("issuetype", {}).get("name", ""),
                    "status": fields.get("status", {}).get("name", ""),
                })
            return issues

    def _adf_to_text(self, node) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            if node.get("type") == "text":
                return node.get("text", "")
            parts = [self._adf_to_text(c) for c in node.get("content", [])]
            newline_types = {
                "paragraph", "heading", "bulletList", "orderedList",
                "listItem", "blockquote", "panel", "rule",
            }
            sep = "\n" if node.get("type") in newline_types else " "
            return sep.join(p for p in parts if p)
        if isinstance(node, list):
            return "\n".join(self._adf_to_text(item) for item in node if item)
        return ""

    async def get_issue(self, issue_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=self._headers,
                params={"fields": "summary,description,issuetype,status,project"},
            )
            if r.status_code == 404:
                raise ValueError(f"Issue {issue_key} not found")
            if r.status_code == 401:
                raise PermissionError("Invalid Jira credentials")
            r.raise_for_status()
            data = r.json()
            fields = data.get("fields", {})

            summary = fields.get("summary", "")
            desc_raw = fields.get("description")
            if isinstance(desc_raw, dict):
                description = self._adf_to_text(desc_raw)
            elif isinstance(desc_raw, str):
                description = desc_raw
            else:
                description = ""

            return {
                "key": data.get("key"),
                "summary": summary,
                "description": description,
                "issue_type": fields.get("issuetype", {}).get("name", ""),
                "status": fields.get("status", {}).get("name", ""),
                "project_key": fields.get("project", {}).get("key", ""),
                "project_name": fields.get("project", {}).get("name", ""),
            }

    def _text_to_adf(self, text: str) -> dict:
        paragraphs = []
        for block in text.split("\n\n"):
            lines = [line for line in block.strip().split("\n") if line.strip()]
            if not lines:
                continue
            content: list = []
            for i, line in enumerate(lines):
                content.append({"type": "text", "text": line})
                if i < len(lines) - 1:
                    content.append({"type": "hardBreak"})
            paragraphs.append({"type": "paragraph", "content": content})
        if not paragraphs:
            paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
        return {"type": "doc", "version": 1, "content": paragraphs}

    async def create_test_set(
        self,
        project_key: str,
        summary: str,
        linked_issue_key: Optional[str] = None,
    ) -> dict:
        """Create a Test Set issue and link it to the source story (requirement)."""
        payload = {
            "fields": {
                "summary": summary[:255],
                "issuetype": {"name": "Test Set"},
                "project": {"key": project_key},
            }
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{self.base_url}/rest/api/3/issue",
                headers=self._headers,
                json=payload,
            )
            # Fallback: if "Test Set" issue type not available, use Task with label
            if r.status_code == 400:
                err = r.text.lower()
                if "issuetype" in err or "issue type" in err:
                    payload["fields"]["issuetype"] = {"name": "Task"}
                    payload["fields"]["labels"] = ["Test-Set"]
                    r = await client.post(
                        f"{self.base_url}/rest/api/3/issue",
                        headers=self._headers,
                        json=payload,
                    )
            r.raise_for_status()
            data = r.json()
            created_key = data.get("key", "")
            created_id = data.get("id", "")

            if linked_issue_key and created_key:
                try:
                    await client.post(
                        f"{self.base_url}/rest/api/3/issueLink",
                        headers=self._headers,
                        json={
                            "type": {"name": "Tests"},
                            "inwardIssue": {"key": created_key},
                            "outwardIssue": {"key": linked_issue_key},
                        },
                    )
                except Exception:
                    pass

            return {
                "key": created_key,
                "id": created_id,
                "url": f"{self.base_url}/browse/{created_key}",
            }

    async def add_tests_to_set(
        self,
        test_set_key: str,
        test_keys: list[str],
        test_set_id: str = "",
        test_ids: Optional[list[str]] = None,
    ) -> bool:
        """Associate Test issues with a Test Set.

        Tries Xray Cloud v2 API first (requires numeric issue IDs + Xray token),
        then Xray Server v1, then standard Jira issue links as last resort.
        """
        if not test_keys:
            return True
        async with httpx.AsyncClient(timeout=20.0) as client:

            # --- Xray Cloud v2 (requires numeric IDs and Xray API token) ---
            token = await self._get_xray_token(client)
            if token and test_set_id and test_ids:
                xray_hdrs = self._xray_headers(token)
                for endpoint in [
                    f"{XRAY_CLOUD_BASE}/testset/{test_set_id}/test",
                    f"{XRAY_CLOUD_BASE}/testset/{test_set_id}/tests",
                ]:
                    try:
                        r = await client.post(
                            endpoint,
                            headers=xray_hdrs,
                            json={"add": test_ids},
                        )
                        logger.info(f"Xray v2 testset link {test_set_key}: {r.status_code} {r.text[:200]}")
                        if r.is_success:
                            return True
                    except Exception as e:
                        logger.warning(f"Xray v2 testset exception: {e}")

            # --- Xray Server/DC v1 ---
            try:
                r = await client.post(
                    f"{self.base_url}/rest/raven/1.0/api/testset/{test_set_key}/test",
                    headers=self._headers,
                    json={"add": test_keys},
                )
                logger.info(f"Xray v1 testset link: {r.status_code} {r.text[:120]}")
                if r.is_success:
                    return True
            except Exception:
                pass

            # --- Last resort: standard Jira issue links ---
            linked = 0
            for test_key in test_keys:
                for link_type in ("Tests", "is member of", "Relates"):
                    try:
                        r = await client.post(
                            f"{self.base_url}/rest/api/3/issueLink",
                            headers=self._headers,
                            json={
                                "type": {"name": link_type},
                                "inwardIssue": {"key": test_key},
                                "outwardIssue": {"key": test_set_key},
                            },
                        )
                        if r.is_success:
                            linked += 1
                            break
                    except Exception:
                        continue
            return linked > 0

    def _parse_test_content(self, content: str) -> dict:
        """Extract structured fields from AI-generated test case markdown."""
        result = {"preconditions": [], "steps": [], "expected_outcome": ""}

        pre = re.search(r'\*\*Preconditions:\*\*\n([\s\S]*?)(?=\n\*\*|\n##|$)', content)
        if pre:
            result["preconditions"] = [
                l.strip().lstrip("- ").strip()
                for l in pre.group(1).split("\n")
                if l.strip().startswith("-")
            ]

        steps_block = re.search(r'\*\*Test Steps:\*\*\n([\s\S]*?)(?=\n\*\*|\n##|$)', content)
        if steps_block:
            rows = [
                l for l in steps_block.group(1).split("\n")
                if "|" in l and not re.match(r'^\s*\|[\s|:-]+\|\s*$', l)
            ]
            for row in rows[1:]:  # skip header
                cols = [c.strip() for c in row.split("|")[1:-1]]
                if len(cols) >= 3 and cols[1]:
                    result["steps"].append({"step": cols[0], "action": cols[1], "expected": cols[2]})

        om = re.search(r'\*\*Expected Outcome:\*\*\s*([^\n]+(?:\n(?!\*\*|\n##)[^\n]+)*)', content)
        if om:
            result["expected_outcome"] = om.group(1).strip()

        return result

    async def test_xray_connection(self) -> dict:
        """Verify Xray Cloud v2 credentials and return diagnostic info."""
        if not self.xray_client_id or not self.xray_client_secret:
            return {"ok": False, "error": "No Xray credentials configured in Admin Settings"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._get_xray_token(client)
            if not token:
                return {"ok": False, "error": "Authentication failed — check Client ID and Secret in Admin Settings"}
            return {
                "ok": True,
                "message": "Xray Cloud v2 authenticated successfully",
                "token_preview": token[:20] + "...",
            }

    async def _push_xray_steps(
        self,
        client: httpx.AsyncClient,
        issue_key: str,
        issue_id: str,
        steps: list,
    ) -> bool:
        """Push test steps to Xray. Tries all known Cloud v2 formats, then v1 fallback."""
        if not steps:
            return True

        token = await self._get_xray_token(client)

        # --- Xray Cloud v2 ---
        if token and issue_id:
            xray_hdrs = self._xray_headers(token)

            # Attempt 1: PUT /steps with array (bulk replace — most common v2 pattern)
            bulk_bodies = [
                # plain text fields
                [{"action": s["action"], "data": "", "result": s["expected"]} for s in steps],
                # raw-wrapped fields
                [{"action": {"raw": s["action"]}, "data": {"raw": ""}, "result": {"raw": s["expected"]}} for s in steps],
            ]
            for bulk in bulk_bodies:
                try:
                    url = f"{XRAY_CLOUD_BASE}/test/{issue_id}/steps"
                    r = await client.put(url, headers=xray_hdrs, json=bulk)
                    logger.info(f"Xray v2 PUT /steps {issue_key}({issue_id}): {r.status_code} {r.text[:300]}")
                    if r.is_success:
                        return True
                except Exception as e:
                    logger.warning(f"Xray v2 PUT /steps exception: {e}")

            # Attempt 2: POST /step one at a time (singular endpoint)
            success = 0
            for s in steps:
                step_bodies = [
                    {"action": s["action"], "data": "", "result": s["expected"]},
                    {"step": s["action"], "data": "", "result": s["expected"]},
                    {"action": {"raw": s["action"]}, "data": {"raw": ""}, "result": {"raw": s["expected"]}},
                ]
                for body in step_bodies:
                    try:
                        url = f"{XRAY_CLOUD_BASE}/test/{issue_id}/step"
                        r = await client.post(url, headers=xray_hdrs, json=body)
                        logger.info(f"Xray v2 POST /step {issue_key}({issue_id}): {r.status_code} {r.text[:300]}")
                        if r.is_success:
                            success += 1
                            break
                    except Exception as e:
                        logger.warning(f"Xray v2 POST /step exception: {e}")
                else:
                    continue
                break
            if success > 0:
                return success == len(steps)

            logger.warning(f"All Xray v2 step attempts failed for {issue_key}({issue_id}) — falling through to v1")

        # --- Xray Server/DC v1 fallback ---
        success = 0
        for s in steps:
            for body in [
                {"step": s["action"], "data": "", "result": s["expected"]},
                {"action": s["action"], "data": "", "result": s["expected"]},
            ]:
                try:
                    r = await client.post(
                        f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}/step",
                        headers=self._headers,
                        json=body,
                    )
                    logger.info(f"Xray v1 step {issue_key}: {r.status_code} {r.text[:200]}")
                    if r.is_success:
                        success += 1
                        break
                except Exception as e:
                    logger.warning(f"Xray v1 step exception: {e}")
        return success == len(steps)

    async def create_xray_test(
        self,
        project_key: str,
        summary: str,
        content: str,
        linked_issue_key: Optional[str] = None,
        issue_type: str = "Test",
    ) -> dict:
        parsed = self._parse_test_content(content)

        # Description: just the expected outcome (steps go into Xray step fields)
        desc_text = parsed["expected_outcome"] or ""
        if parsed["preconditions"]:
            pre_text = "Preconditions:\n" + "\n".join(f"- {p}" for p in parsed["preconditions"])
            desc_text = (pre_text + "\n\n" + desc_text).strip() if desc_text else pre_text

        payload = {
            "fields": {
                "summary": summary[:255],
                "issuetype": {"name": issue_type},
                "project": {"key": project_key},
                "description": self._text_to_adf(desc_text or content),
            }
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{self.base_url}/rest/api/3/issue",
                headers=self._headers,
                json=payload,
            )
            # If "Test" issue type not found, fall back to "Task"
            if r.status_code == 400:
                err_text = r.text.lower()
                if "issuetype" in err_text or "issue type" in err_text:
                    payload["fields"]["issuetype"] = {"name": "Task"}
                    r = await client.post(
                        f"{self.base_url}/rest/api/3/issue",
                        headers=self._headers,
                        json=payload,
                    )
            r.raise_for_status()
            data = r.json()
            created_key = data.get("key", "")
            created_id = data.get("id", "")   # numeric Jira issue ID — needed for Xray Cloud v2
            actual_type = payload["fields"]["issuetype"]["name"]

            # Push test steps into Xray step fields (best-effort)
            if created_key and parsed["steps"] and actual_type == "Test":
                await self._push_xray_steps(client, created_key, created_id, parsed["steps"])

            # Link to source issue
            if linked_issue_key and created_key:
                try:
                    await client.post(
                        f"{self.base_url}/rest/api/3/issueLink",
                        headers=self._headers,
                        json={
                            "type": {"name": "Tests"},
                            "inwardIssue": {"key": created_key},
                            "outwardIssue": {"key": linked_issue_key},
                        },
                    )
                except Exception:
                    pass

            return {
                "key": created_key,
                "id": created_id,
                "url": f"{self.base_url}/browse/{created_key}",
                "issue_type": actual_type,
            }
