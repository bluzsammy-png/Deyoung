"""GitHub connector - least-privilege REST access with a user PAT token."""
from __future__ import annotations

import httpx

from .base import ConnectorAdapter, ConnectorSpec

SPEC = ConnectorSpec(
    name="github",
    version="1.0.0",
    description="Read repositories, files and issues; create issues. Free GitHub API.",
    capabilities=["github_operations", "repository_analysis", "git_operations"],
    auth="api_token",
    scopes=["repo:read (use a fine-grained PAT limited to chosen repos)"],
    rate_limits="5000 req/h authenticated (GitHub official)",
    security=["token stored server-side with 0600", "read-only by default",
              "no git credentials exposed to the Personal AI"],
    free_status="FREE_FOREVER",
    license="API terms of service (free tier)",
    supported_operations=["list_repos", "get_file", "create_issue", "list_issues"],
)


class GitHubConnector(ConnectorAdapter):
    spec = SPEC

    def install(self, config: dict) -> dict:
        token = str(config.get("token") or "")
        if not token or len(token) < 20:
            raise ValueError("config.token must be a GitHub personal access token "
                             "(free; fine-grained, read-only recommended)")
        return {"token": token, "api_base": config.get("api_base", "https://api.github.com")}

    def authorize(self, config: dict) -> dict:
        return {
            "instructions": [
                "1. Open https://github.com/settings/tokens (free)",
                "2. Generate a fine-grained token limited to the repos you want",
                "3. Grant ONLY 'Contents: Read' (+ Issues: Write if needed)",
                "4. Re-run install with {'token': '...'}",
                "Revoke anytime; PATI access dies with the token.",
            ]
        }

    def health_check(self) -> dict:
        try:
            r = httpx.get("https://api.github.com/rate_limit", timeout=10)
            return {"ok": r.status_code == 200, "api": "reachable"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def call(self, op: str, payload: dict, config: dict) -> dict:
        base = config.get("api_base", "https://api.github.com")
        headers = {"Authorization": f"Bearer {config['token']}",
                   "Accept": "application/vnd.github+json"}
        with httpx.Client(base_url=base, headers=headers, timeout=30) as c:
            if op == "list_repos":
                r = c.get("/user/repos", params={"per_page": payload.get("limit", 30)})
                r.raise_for_status()
                return {"repos": [{"name": x["full_name"], "private": x["private"]} for x in r.json()]}
            if op == "get_file":
                owner, repo = payload["repo"].split("/")
                r = c.get(f"/repos/{owner}/{repo}/contents/{payload['path']}")
                r.raise_for_status()
                data = r.json()
                return {"path": data["path"], "size": data["size"],
                        "content": data.get("content", "")}
            if op == "list_issues":
                owner, repo = payload["repo"].split("/")
                r = c.get(f"/repos/{owner}/{repo}/issues", params={"per_page": 20})
                r.raise_for_status()
                return {"issues": [{"number": i["number"], "title": i["title"]} for i in r.json()]}
            if op == "create_issue":
                owner, repo = payload["repo"].split("/")
                r = c.post(f"/repos/{owner}/{repo}/issues",
                           json={"title": payload["title"], "body": payload.get("body", "")})
                r.raise_for_status()
                return {"issue_url": r.json().get("html_url")}
        raise ValueError(f"unsupported operation: {op}")
