# Copyright © 2026 Network Logic Limited. All rights reserved.

import asyncio
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
            if not self.xray_client_id or not self.xray_client_secret:
                logger.warning(f"Xray v2 testset link SKIPPED for {test_set_key}: no Xray credentials")
            elif not test_set_id:
                logger.warning(f"Xray v2 testset link SKIPPED for {test_set_key}: test_set_id is empty")
            elif not test_ids:
                logger.warning(f"Xray v2 testset link SKIPPED for {test_set_key}: test_ids list is empty")
            else:
                token = await self._get_xray_token(client)
                if not token:
                    logger.warning(f"Xray v2 testset link SKIPPED for {test_set_key}: token auth failed")
                else:
                    xray_hdrs = self._xray_headers(token)
                    logger.info(f"Xray v2 linking {len(test_ids)} test(s) to testset {test_set_key}(id={test_set_id})")

                    # Primary: GraphQL API
                    gql = {
                        "query": (
                            "mutation AddTests($issueId:String!,$testIssueIds:[String!]!)"
                            "{addTestsToTestSet(issueId:$issueId,testIssueIds:$testIssueIds)"
                            "{addedTests warning}}"
                        ),
                        "variables": {"issueId": test_set_id, "testIssueIds": test_ids},
                    }
                    try:
                        r = await client.post(f"{XRAY_CLOUD_BASE}/graphql", headers=xray_hdrs, json=gql)
                        logger.info(f"Xray GraphQL addTestsToTestSet {test_set_key}: {r.status_code} {r.text[:400]}")
                        if r.is_success:
                            resp = r.json()
                            if not resp.get("errors"):
                                return True
                            logger.warning(f"Xray GraphQL testset errors: {resp['errors'][:2]}")
                    except Exception as e:
                        logger.warning(f"Xray GraphQL testset exception: {e}")

                    # Fallback: REST API
                    for endpoint in [
                        f"{XRAY_CLOUD_BASE}/testset/{test_set_id}/test",
                        f"{XRAY_CLOUD_BASE}/testset/{test_set_id}/tests",
                    ]:
                        try:
                            r = await client.post(endpoint, headers=xray_hdrs, json={"add": test_ids})
                            logger.info(f"Xray v2 testset REST {test_set_key}: {r.status_code} {r.text[:400]}")
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

    async def _push_steps_graphql(
        self,
        client: httpx.AsyncClient,
        issue_id: str,
        steps: list,
        xray_hdrs: dict,
    ) -> bool:
        """Push test steps via Xray Cloud v2 GraphQL addTestStep mutation (one call per step)."""
        # Xray Cloud v2 GraphQL: addTestStep(issueId, step: CreateStepInput!) per step
        gql_template = (
            "mutation AddStep($issueId:String!,$step:CreateStepInput!)"
            "{addTestStep(issueId:$issueId,step:$step){id action result}}"
        )
        pushed = 0
        for s in steps:
            gql = {
                "query": gql_template,
                "variables": {
                    "issueId": issue_id,
                    "step": {"action": s["action"], "data": "", "result": s["expected"]},
                },
            }
            try:
                r = await client.post(f"{XRAY_CLOUD_BASE}/graphql", headers=xray_hdrs, json=gql)
                logger.info(
                    f"Xray GraphQL addTestStep issueId={issue_id} step={pushed+1}: "
                    f"{r.status_code} {r.text[:300]}"
                )
                if r.is_success:
                    resp = r.json()
                    if not resp.get("errors"):
                        pushed += 1
                        continue
                    logger.warning(f"Xray GraphQL addTestStep errors: {resp['errors'][:2]}")
                    return False
                else:
                    logger.warning(f"Xray GraphQL addTestStep HTTP {r.status_code}: {r.text[:300]}")
                    return False
            except Exception as e:
                logger.warning(f"Xray GraphQL addTestStep exception: {e}")
                return False

        logger.info(f"Xray GraphQL addTestStep: pushed {pushed}/{len(steps)} steps to issueId={issue_id}")
        return pushed == len(steps)

    async def _push_xray_steps(
        self,
        client: httpx.AsyncClient,
        issue_key: str,
        issue_id: str,
        steps: list,
    ) -> bool:
        """Push test steps to Xray Cloud v2 (GraphQL primary, REST fallback)."""
        if not steps:
            return True

        if not self.xray_client_id or not self.xray_client_secret:
            logger.warning(f"Xray steps SKIPPED for {issue_key}: no Xray credentials in Admin → Settings → Xray Cloud API")
            return False
        if not issue_id:
            logger.warning(f"Xray steps SKIPPED for {issue_key}: issue_id is empty (Jira did not return numeric ID)")
            return False

        token = await self._get_xray_token(client)
        if not token:
            logger.warning(f"Xray steps SKIPPED for {issue_key}: token auth failed (check Client ID / Secret in Admin Settings)")
            return False

        xray_hdrs = self._xray_headers(token)
        logger.info(f"Xray v2 pushing {len(steps)} step(s) to {issue_key} (issueId={issue_id})")

        # GraphQL API — the only working method for this Xray Cloud plan
        return await self._push_steps_graphql(client, issue_id, steps, xray_hdrs)

    async def _push_xray_preconditions(
        self,
        client: httpx.AsyncClient,
        project_key: str,
        test_key: str,
        test_id: str,
        preconditions: list[str],
    ) -> bool:
        """Create a Pre-Condition issue and link it to the test via Xray GraphQL."""
        if not preconditions or not self.xray_client_id or not self.xray_client_secret or not test_id:
            return False

        token = await self._get_xray_token(client)
        if not token:
            return False

        # Create the Pre-Condition Jira issue
        pre_text = "\n".join(f"- {p}" for p in preconditions)
        payload = {
            "fields": {
                "summary": f"Preconditions for {test_key}"[:255],
                "issuetype": {"name": "Pre-Condition"},
                "project": {"key": project_key},
                "description": self._text_to_adf(pre_text),
            }
        }
        try:
            r = await client.post(
                f"{self.base_url}/rest/api/3/issue", headers=self._headers, json=payload
            )
            if r.status_code == 400 and ("issuetype" in r.text.lower() or "issue type" in r.text.lower()):
                logger.warning(f"Pre-Condition issue type not available in {project_key}, skipping preconditions")
                return False
            if not r.is_success:
                logger.warning(f"Failed to create Pre-Condition for {test_key}: {r.status_code} {r.text[:200]}")
                return False

            precond_id = r.json().get("id", "")
            precond_key = r.json().get("key", "")
            logger.info(f"Created Pre-Condition {precond_key} (id={precond_id}) for {test_key}")

            # Link via Xray GraphQL addPreconditionsToTest
            xray_hdrs = self._xray_headers(token)
            gql = {
                "query": (
                    "mutation AddPreconditions($issueId:String!,$preconditionIssueIds:[String!]!)"
                    "{addPreconditionsToTest(issueId:$issueId,preconditionIssueIds:$preconditionIssueIds)"
                    "{addedPreconditions warning}}"
                ),
                "variables": {"issueId": test_id, "preconditionIssueIds": [precond_id]},
            }
            r2 = await client.post(f"{XRAY_CLOUD_BASE}/graphql", headers=xray_hdrs, json=gql)
            logger.info(f"Xray GraphQL addPreconditionsToTest {test_key}: {r2.status_code} {r2.text[:300]}")
            if r2.is_success and not r2.json().get("errors"):
                return True
            if r2.is_success:
                logger.warning(f"Xray GraphQL preconditions errors: {r2.json().get('errors', [])[:2]}")
        except Exception as e:
            logger.warning(f"Xray preconditions exception: {e}")
        return False

    async def create_xray_test(
        self,
        project_key: str,
        summary: str,
        content: str,
        linked_issue_key: Optional[str] = None,
        issue_type: str = "Test",
    ) -> dict:
        parsed = self._parse_test_content(content)

        # Description always includes preconditions + expected outcome.
        # Steps go into Xray step fields via the v2 API separately.
        desc_parts: list[str] = []
        if parsed["preconditions"]:
            desc_parts.append("Preconditions:\n" + "\n".join(f"- {p}" for p in parsed["preconditions"]))
        if parsed["expected_outcome"]:
            desc_parts.append(parsed["expected_outcome"])
        desc_text = "\n\n".join(desc_parts) if desc_parts else content

        payload = {
            "fields": {
                "summary": summary[:255],
                "issuetype": {"name": issue_type},
                "project": {"key": project_key},
                "description": self._text_to_adf(desc_text),
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
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
            created_id = data.get("id", "")   # numeric Jira issue ID for Xray Cloud v2
            actual_type = payload["fields"]["issuetype"]["name"]

            if created_key and actual_type == "Test" and parsed["steps"]:
                await self._push_xray_steps(client, created_key, created_id, parsed["steps"])

            if created_key and actual_type == "Test" and parsed["preconditions"]:
                await self._push_xray_preconditions(
                    client, project_key, created_key, created_id, parsed["preconditions"]
                )

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
