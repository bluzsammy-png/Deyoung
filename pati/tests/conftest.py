"""Shared fixtures: a REAL control plane (uvicorn on 127.0.0.1, random port).

The whole suite runs over live HTTP - no mocked API. One throwaway data dir
is created per test session before pati_api imports its config."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn

_TMP_DATA = tempfile.mkdtemp(prefix="pati-test-data-")
os.environ["PATI_DATA_DIR"] = _TMP_DATA
os.environ["PATI_RATE_LIMIT_PER_MIN"] = "100000"  # per-test override where needed

from pati import PatiClient  # noqa: E402
from pati_api import config  # noqa: E402
from pati_api import db, security  # noqa: E402
from pati_api.app import app  # noqa: E402


@pytest.fixture(scope="session")
def server():
    db.reset_db()
    db.init_db()
    token = security.bootstrap_admin_token()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    port = srv.servers[0].sockets[0].getsockname()[1]
    yield {"base_url": f"http://127.0.0.1:{port}", "admin_token": token}
    srv.should_exit = True
    th.join(timeout=5)


@pytest.fixture(scope="session")
def admin(server):
    return PatiClient(server["base_url"], token=server["admin_token"])


@pytest.fixture()
def client_factory(server):
    created = []

    def make(token: str) -> PatiClient:
        c = PatiClient(server["base_url"], token=token)
        created.append(c)
        return c

    yield make
    for c in created:
        c.close()


@pytest.fixture()
def workspace(tmp_path):
    ws = tmp_path / "PATI_workspace"
    ws.mkdir()
    return ws


class LocalAgentRunner:
    """Runs a real PatiAgent against the live server in background threads."""

    def __init__(self, server_url: str, admin: PatiClient, workspace: Path,
                 name: str = "local-agent-pc",
                 permissions: list[str] | None = None, fail_first_job: bool = False):
        from pati_agent.agent import PatiAgent
        from pati_agent.api_client import AgentAPI
        from pati_agent.audit import AuditLog
        from pati_agent.config import AgentConfig
        from pati_agent.policy import DEFAULT_PERMISSIONS

        probe = AgentConfig(allowed_roots=[str(workspace)],
                            permissions=permissions or list(DEFAULT_PERMISSIONS))
        reg = admin.register_worker(
            name=name, wtype="LOCAL_WORKER",
            capabilities=probe.policy_engine().capabilities(),
        )
        self.worker_id = reg["worker_id"]
        token = reg["token"]
        cfg = AgentConfig(server_url=server_url, worker_id=self.worker_id, token=token,
                          worker_name=name,
                          allowed_roots=[str(workspace)],
                          permissions=permissions or list(DEFAULT_PERMISSIONS))
        self.cfg = cfg
        self.workspace = workspace
        self.fail_first_job = fail_first_job
        self._failures_left = 1 if fail_first_job else 0
        data_dir = workspace.parent / "agent-data"
        data_dir.mkdir(exist_ok=True)
        self.audit = AuditLog(data_dir / "audit.jsonl")
        self.api = AgentAPI(server_url, token)
        self.agent = PatiAgent(cfg, self.audit, self.api)

    def start(self):
        self.agent.start()

    def stop(self):
        self.agent.stop()

    @property
    def executed(self):
        return self.agent.executed if hasattr(self.agent, "executed") else []


@pytest.fixture()
def agent_factory(server, admin):
    made = []

    def make(workspace, name="local-agent-pc", permissions=None):
        runner = LocalAgentRunner(server["base_url"], admin, workspace, name, permissions)
        made.append(runner)
        return runner

    yield make
    for r in made:
        try:
            r.stop()
        except Exception:
            pass


class MockGPUWorker:
    """A real remote worker over HTTP with deterministic simulated inference.

    Exercises the exact pull-worker protocol a free Kaggle GPU worker uses:
    register -> heartbeat -> long-poll -> execute -> upload artifacts.
    """

    CAPS = ["text_generation", "storyboard_generation", "image_generation",
            "image_to_video", "text_to_speech", "music_generation", "video_editing",
            "testing", "code_generation", "web_research", "research_synthesis"]

    def __init__(self, server_url: str, admin: PatiClient, name: str = "kaggle-gpu-01",
                 fail_first_job: bool = False):
        reg = admin.register_worker(name=name, wtype="KAGGLE_WORKER", capabilities=self.CAPS)
        self.worker_id = reg["worker_id"]
        self.name = name
        self.fail_first = 1 if fail_first_job else 0
        self.failed_jobs = 0
        self.client = PatiClient(server_url, token=reg["token"])
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.executed: list[str] = []
        self._files: dict[str, Path] = {}

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        try:  # mark the worker row offline immediately (no ghost workers)
            self.client._http.post(f"/api/v1/workers/{self.worker_id}/shutdown", json={})
        except Exception:
            pass
        self.client.close()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.client._http.post(f"/api/v1/workers/{self.worker_id}/heartbeat",
                                       json={"resources": {"gpu": "simulated-free-T4"}}
                                       ).raise_for_status()
                resp = self.client._http.get(
                    f"/api/v1/workers/{self.worker_id}/jobs/next",
                    params={"wait": 1}, timeout=30)
                resp.raise_for_status()
                job = resp.json().get("job")
            except Exception:
                self._stop.wait(0.8)
                continue
            if job:
                try:
                    self._handle(job)
                except Exception:
                    pass

    def _handle(self, job: dict):
        import tempfile
        op = job["op"]
        stage = job.get("stage_name") or op
        self.executed.append(stage)

        if self.fail_first > 0:
            self.fail_first -= 1
            self.failed_jobs += 1
            data = {"status": "FAILED", "result": "{}",
                    "error": "transient kernel boot failure", "error_code": "TRANSIENT",
                    "artifacts_meta": "[]"}
            self.client._http.post(
                f"/api/v1/workers/{self.worker_id}/jobs/{job['job_id']}/complete",
                data=data).raise_for_status()
            return

        result: dict = {}
        artifacts: list[dict] = []
        tmp = Path(tempfile.mkdtemp(prefix="pati-gpuworker-"))
        kind_map = {"generate_image": "image", "generate_video": "video",
                    "generate_speech": "audio", "generate_music": "audio",
                    "render_video": "video"}
        if op in ("generate_text", "generate_code"):
            prompt = str(job["params"].get("prompt") or "")[:120]
            text = (f"[SIMULATED MODEL OUTPUT] stage={stage} prompt={prompt}")
            result = {"text": text, "simulated": True}
        elif op in ("run_tests", "validate_video"):
            result = {"ok": True, "validated": job["params"].get("target"), "simulated": True}
        elif op in kind_map:
            kind = kind_map[op]
            ext = {"image": "png", "video": "mp4", "audio": "wav"}[kind]
            data_bytes = f"PATI SIMULATED {kind.upper()} stage={stage}".encode() * 32
            fname = f"{stage}.{ext}"
            f = tmp / fname
            f.write_bytes(data_bytes)
            self._files[fname] = f
            artifacts = [{"name": fname, "type": kind, "file": fname,
                          "mime": {"image": "image/png", "video": "video/mp4",
                                   "audio": "audio/wav"}[kind]}]
            result = {"stage": stage, "simulated": True}
        else:
            data = {"status": "FAILED", "result": json.dumps(result),
                    "error": f"mock worker cannot handle op {op}", "error_code": "UNSUPPORTED_OP",
                    "artifacts_meta": "[]"}
            self.client._http.post(
                f"/api/v1/workers/{self.worker_id}/jobs/{job['job_id']}/complete",
                data=data).raise_for_status()
            return

        files = [("files", (a["file"], open(self._files[a["file"]], "rb")))
                 for a in artifacts]
        ok_data = {"status": "SUCCEEDED", "result": json.dumps(result), "error": "",
                   "error_code": "", "artifacts_meta": json.dumps(artifacts)}
        self.client._http.post(
            f"/api/v1/workers/{self.worker_id}/jobs/{job['job_id']}/complete",
            data=ok_data, files=files).raise_for_status()
        for _, fh in files:
            fh[1].close()


@pytest.fixture()
def gpu_worker(server, admin):
    w = MockGPUWorker(server["base_url"], admin)
    w.start()
    yield w
    w.stop()
