# Copyright © 2026 Network Logic Limited. All rights reserved.

import base64
import httpx
from typing import Optional


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        encoded = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

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
        """Return recent issues for a project (newest first).

        Uses the new /rest/api/3/search/jql endpoint — the old
        /rest/api/3/search was deprecated by Atlassian and now returns 410 Gone.
        """
        jql = f'project = "{project_key}" ORDER BY updated DESC'
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

    def _parse_test_content(self, content: str) -> dict:
        """
        Parse AI-generated markdown for TEST_CASES / NEGATIVE_TEST_CASES.
        Returns {'preconditions': [str], 'steps': [{'action': str, 'expected': str}]}
        """
        import re
        result: dict = {"preconditions": [], "steps": []}

        # Extract bullet-list preconditions
        prec_match = re.search(
            r"\*\*Preconditions?\*\*[:\s]*\n((?:\s*[-•]\s*.+\n?)+)",
            content, re.IGNORECASE | re.MULTILINE,
        )
        if prec_match:
            for line in prec_match.group(1).splitlines():
                item = line.strip().lstrip("-•").strip()
                if item:
                    result["preconditions"].append(item)

        # Extract rows from markdown table  |  n  |  action  |  expected  |
        for row in re.finditer(
            r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
            content, re.MULTILINE,
        ):
            action, expected = row.group(1).strip(), row.group(2).strip()
            if action and not action.startswith("---") and action.lower() != "action":
                result["steps"].append({"action": action, "expected": expected})

        return result

    async def _push_xray_steps(
        self,
        issue_key: str,
        preconditions: list[str],
        steps: list[dict],
    ) -> None:
        """
        Populate Xray test steps and precondition definition.
        Best-effort — silently skips on any API error so the issue is still useful.
        """
        if not steps and not preconditions:
            return
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Set precondition definition text on the test issue
                if preconditions:
                    defn = "\n".join(f"- {p}" for p in preconditions)
                    await client.put(
                        f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}",
                        headers=self._headers,
                        json={"definition": defn},
                    )

                # Add each step in order
                for idx, step in enumerate(steps, 1):
                    await client.post(
                        f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}/step",
                        headers=self._headers,
                        json={
                            "index": idx,
                            "step": step["action"],
                            "data": "",
                            "result": step["expected"],
                        },
                    )
        except Exception:
            pass  # best-effort — don't fail the whole push

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

    async def create_xray_test(
        self,
        project_key: str,
        summary: str,
        content: str,
        linked_issue_key: Optional[str] = None,
        issue_type: str = "Test",
        generation_type: str = "",
    ) -> dict:
        # For step-based types, parse structured content before creating the issue.
        # The description will contain the full AI output for human reference;
        # the Xray step fields are populated separately via the Xray REST API.
        STEP_TYPES = {"TEST_CASES", "NEGATIVE_TEST_CASES"}
        parsed = self._parse_test_content(content) if generation_type.upper() in STEP_TYPES else None

        payload = {
            "fields": {
                "summary": summary[:255],
                "issuetype": {"name": issue_type},
                "project": {"key": project_key},
                "description": self._text_to_adf(content),
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
            actual_type = payload["fields"]["issuetype"]["name"]

            # Populate Xray test steps and preconditions (best-effort)
            if created_key and parsed and (parsed["steps"] or parsed["preconditions"]):
                await self._push_xray_steps(
                    created_key, parsed["preconditions"], parsed["steps"]
                )

            # Link to source issue — best-effort (Xray "Tests" link type)
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
                "url": f"{self.base_url}/browse/{created_key}",
                "issue_type": actual_type,
                "steps_pushed": len(parsed["steps"]) if parsed else 0,
                "preconditions_pushed": len(parsed["preconditions"]) if parsed else 0,
            }
