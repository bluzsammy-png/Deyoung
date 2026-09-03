"""Universal worker interface (REGISTER, HEALTH, CAPABILITIES, RESOURCES,
SUBMIT, STATUS, CANCEL, LOGS, ARTIFACTS, HEARTBEAT, SHUTDOWN).

Two worker styles implement the same contract:

- PullWorker: dials the control plane, long-polls jobs (Local Agent, any
  remote free worker behind NAT). Outbound-only - works from a home PC.
- PushWorker (Kaggle): the control-plane-side adapter submits batch jobs to
  an external free service and polls for results.

PATI is always the controller; Kaggle/Colab are ephemeral batch compute.
"""
from __future__ import annotations

import abc
import enum


class WorkerOp(str, enum.Enum):
    REGISTER = "REGISTER"
    HEALTH = "HEALTH"
    CAPABILITIES = "CAPABILITIES"
    RESOURCES = "RESOURCES"
    SUBMIT = "SUBMIT"
    STATUS = "STATUS"
    CANCEL = "CANCEL"
    LOGS = "LOGS"
    ARTIFACTS = "ARTIFACTS"
    HEARTBEAT = "HEARTBEAT"
    SHUTDOWN = "SHUTDOWN"


class UniversalWorkerInterface(abc.ABC):
    """Every worker type must honor this contract (see docs/WORKER_SPEC.md)."""

    @abc.abstractmethod
    def register(self) -> dict: ...
    @abc.abstractmethod
    def health(self) -> dict: ...
    @abc.abstractmethod
    def capabilities(self) -> list[str]: ...
    @abc.abstractmethod
    def resources(self) -> dict: ...
    @abc.abstractmethod
    def submit(self, job: dict) -> dict: ...
    @abc.abstractmethod
    def status(self, job_id: str) -> dict: ...
    @abc.abstractmethod
    def cancel(self, job_id: str) -> dict: ...
    @abc.abstractmethod
    def logs(self, job_id: str) -> list[dict]: ...
    @abc.abstractmethod
    def artifacts(self, job_id: str) -> list[dict]: ...
    @abc.abstractmethod
    def heartbeat(self) -> dict: ...
    @abc.abstractmethod
    def shutdown(self) -> dict: ...


class BasePullWorker(UniversalWorkerInterface):
    """Shared plumbing for pull-style workers that speak the PATI HTTP protocol."""

    def __init__(self, server_url: str, token: str, name: str, wtype: str,
                 capabilities: list[str]):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.name = name
        self.wtype = wtype
        self.capabilities = capabilities
        self.worker_id = ""
        import httpx
        self._http = httpx.Client(base_url=self.server_url, timeout=40,
                                  headers={"Authorization": f"Bearer {token}"})

    # -- registration / lifecycle ------------------------------------------------
    def register(self) -> dict:
        r = self._http.post("/api/v1/workers/register", json={
            "name": self.name, "type": self.wtype, "capabilities": self.capabilities,
            "machine": {"kind": "pull-worker"}})
        r.raise_for_status()
        data = r.json()
        self.worker_id = data["worker_id"]
        self._http.headers["Authorization"] = f"Bearer {data['token']}"
        return data

    def health(self) -> dict:
        r = self._http.get("/health")
        r.raise_for_status()
        return r.json()

    def capabilities(self) -> list[str]:
        return list(self.capabilities)

    def resources(self) -> dict:
        return {"kind": self.wtype}

    def heartbeat(self) -> dict:
        r = self._http.post(f"/api/v1/workers/{self.worker_id}/heartbeat",
                            json={"resources": self.resources()})
        r.raise_for_status()
        return r.json()

    def shutdown(self) -> dict:
        try:
            self._http.post(f"/api/v1/workers/{self.worker_id}/shutdown", json={})
        finally:
            return {"ok": True}

    # -- pull-style submit/status: jobs arrive via long-poll ---------------------
    def submit(self, job: dict) -> dict:  # noqa: D102 - pull workers receive jobs
        return job

    def status(self, job_id: str) -> dict:
        return {"job_id": job_id, "style": "pull"}

    def cancel(self, job_id: str) -> dict:
        return {"ok": True}

    def logs(self, job_id: str) -> list[dict]:
        return []

    def artifacts(self, job_id: str) -> list[dict]:
        return []
