"""HTTP client the Local Agent uses to talk to the PATI control plane.

Outbound-only: the agent dials the control plane (never listens), which is
safe behind NAT/firewalls and is what makes the Windows install secure.
"""
from __future__ import annotations

import time
import typing as t
from pathlib import Path

import httpx


class AgentAPIError(Exception):
    pass


class AgentAPI:
    def __init__(self, server_url: str, token: str, timeout: float = 40.0):
        self.server_url = server_url.rstrip("/")
        self._http = httpx.Client(base_url=self.server_url, timeout=timeout,
                                  headers={"Authorization": f"Bearer {token}"})

    # ---------------------------------------------------------------- basics
    def health(self) -> dict:
        return self._http.get("/health").json()

    def _retry(self, fn, tries: int = 3, base_delay: float = 1.0):
        last = None
        for i in range(tries):
            try:
                return fn()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
                last = e
                time.sleep(base_delay * (2 ** i))
        raise AgentAPIError(f"server unreachable after {tries} tries: {last}")

    # --------------------------------------------------------------- worker
    def register(self, name: str, wtype: str, capabilities: list[str],
                 pairing_code: str | None = None, machine: dict | None = None) -> dict:
        body = {"name": name, "type": wtype, "capabilities": capabilities,
                "machine": machine or {}}
        if pairing_code:
            body["pairing_code"] = pairing_code
            headers = {"Authorization": ""}
            resp = self._retry(lambda: self._http.post("/api/v1/workers/register", json=body,
                                                       headers=headers))
        else:
            resp = self._retry(lambda: self._http.post("/api/v1/workers/register", json=body))
        resp.raise_for_status()
        return resp.json()

    def heartbeat(self, worker_id: str, resources: dict, health: str | None = None,
                  capabilities: list[str] | None = None) -> dict:
        body = {"resources": resources, "health": health}
        if capabilities is not None:
            body["capabilities"] = capabilities
        resp = self._retry(lambda: self._http.post(
            f"/api/v1/workers/{worker_id}/heartbeat", json=body))
        resp.raise_for_status()
        return resp.json()

    def next_job(self, worker_id: str, wait_s: int = 25) -> dict | None:
        def call():
            r = self._http.get(f"/api/v1/workers/{worker_id}/jobs/next",
                               params={"wait": wait_s}, timeout=wait_s + 20)
            r.raise_for_status()
            return r.json().get("job")
        return self._retry(call, tries=2, base_delay=2.0)

    def job_status(self, worker_id: str, job_id: str, logs: list[dict] | None = None) -> dict:
        r = self._http.post(f"/api/v1/workers/{worker_id}/jobs/{job_id}/status",
                            json={"status": "RUNNING", "logs": logs or []})
        r.raise_for_status()
        return r.json()

    def job_logs(self, worker_id: str, job_id: str, logs: list[dict]) -> dict:
        r = self._http.post(f"/api/v1/workers/{worker_id}/jobs/{job_id}/logs",
                            json={"logs": logs})
        r.raise_for_status()
        return r.json()

    def complete_job(self, worker_id: str, job_id: str, status: str,
                     result: dict | None = None, error: str = "",
                     error_code: str = "", artifacts: list[dict] | None = None) -> dict:
        """artifacts: [{name,type,mime,path(local file to upload)|path_ref, size, checksum}]"""
        data = {"status": status, "result": __import__("json").dumps(result or {}),
                "error": error, "error_code": error_code, "artifacts_meta": "[]"}
        files = []
        meta = []
        for a in artifacts or []:
            if a.get("path") and Path(a["path"]).exists():
                meta.append({"name": a["name"], "type": a.get("type", "file"),
                             "mime": a.get("mime", "application/octet-stream"),
                             "file": Path(a["path"]).name,
                             "metadata": a.get("metadata", {})})
                files.append((Path(a["path"]).name, open(a["path"], "rb")))
            else:
                meta.append({k: v for k, v in a.items() if k in
                             ("name", "type", "mime", "path_ref", "size", "checksum", "metadata")})
        import json as _json
        data["artifacts_meta"] = _json.dumps(meta)
        try:
            if files:
                r = self._http.post(f"/api/v1/workers/{worker_id}/jobs/{job_id}/complete",
                                    data=data,
                                    files=[("files", (n, fh)) for n, fh in files])
            else:
                r = self._http.post(f"/api/v1/workers/{worker_id}/jobs/{job_id}/complete",
                                    data=data)
            r.raise_for_status()
            return r.json()
        finally:
            for _, fh in files:
                try:
                    fh.close()
                except OSError:
                    pass

    def get_artifact(self, artifact_id: str) -> dict:
        import json as _json
        r = self._http.get(f"/api/v1/artifacts/{artifact_id}")
        r.raise_for_status()
        meta = r.json()
        for key in ("provenance", "metadata"):
            if isinstance(meta.get(key), str):
                try:
                    meta[key] = _json.loads(meta[key])
                except _json.JSONDecodeError:
                    meta[key] = {}
        return meta

    def download_artifact(self, artifact_id: str, dest: Path) -> None:
        with self._http.stream("GET", f"/api/v1/artifacts/{artifact_id}/content") as r:
            if r.status_code >= 400:
                raise AgentAPIError(f"download failed: HTTP {r.status_code}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes(64 * 1024):
                    fh.write(chunk)

    def push_audit(self, worker_id: str, events: list[dict]) -> dict:
        try:
            r = self._http.post(f"/api/v1/workers/{worker_id}/audit",
                                json={"events": events[-100:]})
            r.raise_for_status()
            return r.json()
        except Exception:
            return {"ok": False}  # audit is local-first; central push is best-effort

    def shutdown(self, worker_id: str) -> None:
        try:
            self._http.post(f"/api/v1/workers/{worker_id}/shutdown", json={})
        except Exception:
            pass
