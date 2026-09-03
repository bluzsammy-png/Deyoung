"""PatiClient: high-level SDK operations (see docs/API_SPEC.md).

Example:
    from pati import PatiClient
    pati = PatiClient("http://127.0.0.1:8000", token="pati_client_...")
    task = pati.submit_task("Create a folder called YouTube Project 01 in my "
                            "authorized Video Projects directory")
    done = pati.wait_for_task(task["id"], timeout_s=600)
"""
from __future__ import annotations

import base64
import time
import typing as t

import httpx

from .errors import APIError, RateLimited

DEFAULT_TIMEOUT = 30.0


class PatiClient:
    def __init__(self, base_url: str, token: str, timeout: float = DEFAULT_TIMEOUT,
                 api_prefix: str = "/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout,
                                  headers={"Authorization": f"Bearer {token}"})

    # ------------------------------------------------------------------ core
    def _url(self, path: str) -> str:
        return f"{self.api_prefix}{path}"

    def _request(self, method: str, path: str, **kw) -> t.Any:
        resp = self._http.request(method, self._url(path), **kw)
        if resp.status_code == 429:
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = ""
            if "quota" in str(detail).lower():
                raise APIError(429, "QUOTA_EXCEEDED", str(detail))
            raise RateLimited()
        if resp.status_code >= 400:
            detail = None
            code = "HTTP_ERROR"
            message = resp.reason_phrase or "request failed"
            try:
                body = resp.json()
                if isinstance(body, dict):
                    err = body.get("error")
                    if isinstance(err, dict):
                        code, message = err.get("code", code), err.get("message", message)
                        detail = err.get("detail")
                    else:
                        message = body.get("detail", message)
                        detail = body
            except Exception:
                pass
            raise APIError(resp.status_code, code, message, detail)
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ------------------------------------------------------------- lifecycle
    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ------------------------------------------------------------ high level
    def health(self) -> dict:
        return self._http.get("/health").json()

    def get_system_status(self) -> dict:
        return self._request("GET", "/system/status")

    def get_capabilities(self) -> list[dict]:
        return self._request("GET", "/capabilities")["capabilities"]

    def list_models(self) -> list[dict]:
        return self._request("GET", "/models")["models"]

    def list_tools(self) -> list[dict]:
        return self._request("GET", "/tools")["tools"]

    def discover_tool(self, query: str) -> list[dict]:
        return self._request("GET", "/tools/discover", params={"q": query})["results"]

    def install_tool(self, tool_id: str) -> dict:
        return self._request("POST", "/tools/install", json={"tool_id": tool_id})

    def list_workers(self) -> list[dict]:
        return self._request("GET", "/workers")["workers"]

    def get_quotas(self) -> dict:
        return self._request("GET", "/quotas")

    # ----------------------------------------------------------------- tasks
    def submit_task(self, objective: str, task_type: str = "auto", params: dict = None,
                    constraints: dict = None, title: str = None) -> dict:
        return self._request("POST", "/tasks", json={
            "objective": objective, "type": task_type, "params": params or {},
            "constraints": constraints or {}, "title": title})

    def create_task(self, objective: str, **kw) -> dict:  # alias per master prompt
        return self.submit_task(objective, **kw)

    def get_task(self, task_id: str) -> dict:
        return self._request("GET", f"/tasks/{task_id}")

    def cancel_task(self, task_id: str) -> dict:
        return self._request("POST", f"/tasks/{task_id}/cancel")

    def get_task_logs(self, task_id: str, since: int = 0) -> dict:
        return self._request("GET", f"/tasks/{task_id}/logs", params={"since": since})

    def list_tasks(self, status: str = "", limit: int = 50) -> list[dict]:
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._request("GET", "/tasks", params=params)["tasks"]

    def wait_for_task(self, task_id: str, timeout_s: float = 600,
                      poll_s: float = 1.0, on_log=None) -> dict:
        """Poll until terminal state; optionally stream logs via callback."""
        deadline = time.time() + timeout_s
        cursor = 0
        while time.time() < deadline:
            if on_log:
                batch = self.get_task_logs(task_id, since=cursor)
                for entry in batch["logs"]:
                    on_log(entry)
                cursor = batch["next_since"]
            task = self.get_task(task_id)
            if task["status"] in ("COMPLETED", "FAILED", "CANCELLED", "QUARANTINED"):
                return task
            time.sleep(poll_s)
        raise APIError(504, "TIMEOUT", f"task {task_id} did not finish in {timeout_s}s")

    # ------------------------------------------------------------- artifacts
    def get_artifact(self, artifact_id: str) -> dict:
        return self._request("GET", f"/artifacts/{artifact_id}")

    def download_artifact(self, artifact_id: str, dest: str) -> str:
        resp = self._http.get(self._url(f"/artifacts/{artifact_id}/content"))
        if resp.status_code == 409:
            info = resp.json().get("detail", {})
            raise APIError(409, "LOCAL_REFERENCE",
                           f"artifact bytes are local to the agent at: {info.get('path')}", info)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            fh.write(resp.content)
        return dest

    def upload_artifact(self, path: str, name: str = None, task_id: str = "",
                        type_: str = "file") -> dict:
        with open(path, "rb") as fh:
            return self._request("POST", "/artifacts",
                                 data={"name": name or path.split("/")[-1].split("\\")[-1],
                                       "task_id": task_id, "type": type_},
                                 files={"file": fh})

    def list_task_artifacts(self, task_id: str) -> list[dict]:
        return self._request("GET", f"/tasks/{task_id}/artifacts")["artifacts"]

    # -------------------------------------------------------------- research
    def submit_research(self, query: str, mode: str = "local_corpus",
                        save_to: str = None) -> dict:
        return self._request("POST", "/research",
                             json={"query": query, "mode": mode, "save_to": save_to})

    # ------------------------------------------------------------ connectors
    def list_connectors(self) -> list[dict]:
        return self._request("GET", "/connectors")["connectors"]

    def install_connector(self, name: str, config: dict = None) -> dict:
        return self._request("POST", f"/connectors/{name}/install", json={"config": config or {}})

    def call_connector(self, name: str, op: str, payload: dict = None) -> dict:
        return self._request("POST", f"/connectors/{name}/operations/{op}", json=payload or {})

    # ----------------------------------------------------------------- admin
    def create_pairing_code(self) -> dict:
        return self._request("POST", "/admin/pairing-codes", json={})

    def issue_token(self, name: str, kind: str = "client", scopes: list = None) -> dict:
        return self._request("POST", "/admin/tokens",
                             json={"name": name, "kind": kind, "scopes": scopes})

    # ------------------------------------------------------------ workers op
    def register_worker(self, name: str, wtype: str, capabilities: list[str],
                        pairing_code: str = None, machine: dict = None) -> dict:
        """Register a worker. With pairing_code no prior token is required."""
        old_auth = self._http.headers.get("Authorization")
        if pairing_code and not old_auth:
            self._http.headers.pop("Authorization", None)
        try:
            return self._request("POST", "/workers/register", json={
                "name": name, "type": wtype, "capabilities": capabilities,
                "pairing_code": pairing_code, "machine": machine or {}})
        finally:
            if pairing_code and not old_auth and "Authorization" not in self._http.headers:
                pass
            if old_auth:
                self._http.headers["Authorization"] = old_auth
