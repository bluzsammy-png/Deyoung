"""The Local Agent worker loop.

Architecture (per master spec):

    Personal AI -> PATI API -> authenticated control plane
        -> authenticated Local Agent (this process, outbound-only)
        -> policy check -> authorized operation -> result -> PATI -> Personal AI

The agent is a normal PATI worker: it registers, heartbeats with resource
reports, long-polls for jobs, enforces the local policy engine, executes
authorized operations, streams logs and returns artifacts.
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from pathlib import Path

from .api_client import AgentAPI
from .audit import AuditLog
from .config import AgentConfig
from .execops import ExecOperations
from .fsops import FSOperations
from .policy import PolicyViolation
from .sysinfo import machine_profile, resource_report


class PatiAgent:
    def __init__(self, cfg: AgentConfig, audit: AuditLog, api: AgentAPI,
                 poll_forever: bool = True):
        self.cfg = cfg
        self.audit = audit
        self.api = api
        self.poll_forever = poll_forever
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.engine = cfg.policy_engine()
        self.fs = FSOperations(self.engine, self.audit)
        self.exec = ExecOperations(self.engine, self.audit)
        self._audit_cursor = 0

    # ------------------------------------------------------------------ init
    @classmethod
    def from_config(cls, cfg: AgentConfig, poll_forever: bool = True) -> "PatiAgent":
        data_dir = cfg_data_dir(cfg)
        audit = AuditLog(data_dir / "audit.jsonl")
        api = AgentAPI(cfg.server_url, cfg.token)
        agent = cls(cfg, audit=audit, api=api, poll_forever=poll_forever)
        return agent

    def capabilities(self) -> list[str]:
        return self.engine.capabilities()

    # ----------------------------------------------------------------- hooks
    def start(self) -> None:
        self._stop.clear()
        hb = threading.Thread(target=self._heartbeat_loop, name="pati-heartbeat", daemon=True)
        jl = threading.Thread(target=self._job_loop, name="pati-jobs", daemon=True)
        self._threads = [hb, jl]
        hb.start()
        jl.start()

    def stop(self) -> None:
        self._stop.set()
        if self.api and self.cfg.worker_id:
            self.api.shutdown(self.cfg.worker_id)

    def wait(self, timeout: float | None = None) -> None:
        start = time.time()
        while (self._threads and all(t.is_alive() for t in self._threads)):
            if timeout and time.time() - start > timeout:
                return
            time.sleep(0.2)

    # --------------------------------------------------------------- threads
    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            try:
                roots = self.cfg.allowed_roots
                res = resource_report(roots)
                self.api.heartbeat(self.cfg.worker_id, res,
                                   capabilities=self.capabilities())
            except Exception:
                pass
            self._stop.wait(self.cfg.heartbeat_interval_s)

    def _job_loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self.api.next_job(self.cfg.worker_id, self.cfg.longpoll_wait_s)
            except Exception:
                self._stop.wait(3.0)
                continue
            if not job:
                continue
            if not self.poll_forever:
                self._handle_job(job)
                return
            threading.Thread(target=self._handle_job, args=(job,), daemon=True).start()

    # ------------------------------------------------------------------ jobs
    def _handle_job(self, job: dict) -> None:
        job_id = job["job_id"]
        task_id = job["task_id"]
        logs: list[dict] = []

        def log(msg: str, level: str = "info"):
            entry = {"level": level, "message": f"[{job.get('stage_name')}] {msg}"}
            logs.append(entry)
            print(entry["message"], flush=True)

        log(f"job received: op={job.get('op')} capability={job.get('capability')}")
        try:
            params = dict(job.get("params") or {})
            inputs = params.pop("inputs", {}) or {}
            op = job["op"]

            if op == "sim.text_generate":
                result = sim_text(params, inputs, log)
            elif op == "sim.image_generate":
                result = sim_media(params, inputs, "image", log)
            elif op == "sim.video_render":
                result = sim_media(params, inputs, "video", log)
            elif op == "sim.tts":
                result = sim_media(params, inputs, "audio", log)
            elif op == "sim.music":
                result = sim_media(params, inputs, "audio", log)
            elif op == "generate_text":
                result = sim_text({"prompt": json.dumps(inputs) or params.get("prompt", "")},
                                  inputs, log)
            elif op == "generate_image":
                result = sim_media({"prompt": params.get("prompt", "image")}, inputs, "image", log)
            elif op == "generate_video":
                result = sim_media(params, inputs, "video", log)
            elif op == "render_video":
                result = sim_media(params, inputs, "video", log)
            elif op == "generate_speech":
                result = sim_media(params, inputs, "audio", log)
            elif op == "generate_music":
                result = sim_media(params, inputs, "audio", log)
            elif op == "generate_code":
                result = sim_text({"prompt": inputs.get("spec", {}).get("text", "code")}, inputs, log)
            elif op == "run_tests":
                result = {"ok": True, "note": "simulated QA pass (labeled simulated)"}
            elif op == "validate_video":
                result = {"ok": True, "validated": params.get("target")}
            elif op == "sys.report":
                result = resource_report(self.cfg.allowed_roots)
            elif op == "transcribe_audio":
                result = {"ok": False, "error": "RESOURCE_UNAVAILABLE: no free speech_to_text "
                                                "resource configured (add a Kaggle worker)"}
            elif op in ("web.search", "web_scrape"):
                result = {"ok": False, "error": "RESOURCE_UNAVAILABLE: web research connector "
                                                "not installed (free options documented)"}
            else:
                result = self.fs.handle(op, params, inputs=inputs, api=self.api)
            artifacts = result.pop("artifacts", [])
            log("job finished successfully")
            self.api.complete_job(self.cfg.worker_id, job_id, "SUCCEEDED",
                                  result=result, artifacts=artifacts)
        except PolicyViolation as e:
            log(f"POLICY VIOLATION: {e}", level="error")
            self.audit.append("job.policy_violation", resource=str(job.get("op")),
                              detail={"error": str(e)})
            self.api.complete_job(self.cfg.worker_id, job_id, "FAILED",
                                  error=str(e), error_code="SECURITY_VIOLATION")
        except Exception as e:
            log(f"job failed: {e}", level="error")
            traceback.print_exc()
            self.api.complete_job(self.cfg.worker_id, job_id, "FAILED", error=str(e))
        finally:
            if logs:
                try:
                    self.api.job_logs(self.cfg.worker_id, job_id, logs)
                except Exception:
                    pass
            self._flush_audit()

    def _flush_audit(self) -> None:
        try:
            records = self.audit.tail(500)
            new = records[self._audit_cursor:]
            if new:
                self.api.push_audit(self.cfg.worker_id, new)
                self._audit_cursor = len(records)
        except Exception:
            pass


def cfg_data_dir(cfg: AgentConfig) -> Path:
    p = Path.home() / ("PATI/agent" if __import__("os").name == "nt" else ".pati/agent")
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Simulated engines (clearly labeled; real free models arrive via the Kaggle
# worker using the exact same job protocol - see pati_workers/kaggle_worker.py)
# ---------------------------------------------------------------------------
def sim_text(params: dict, inputs: dict, log) -> dict:
    prompt = params.get("prompt") or json.dumps(inputs)[:200] or "generate"
    text = (f"[PATI SIMULATED TEXT - deterministic, labeled simulated]\n"
            f"Objective/prompt: {prompt[:400]}\n"
            f"Outline: 1) setup 2) development 3) resolution.\n"
            f"Note: replace with a free open-weights model via the Kaggle worker "
            f"or a local runtime; the job protocol is identical.")
    return {"text": text, "simulated": True}


def sim_media(params: dict, inputs: dict, kind: str, log) -> dict:
    label = {"image": "PNG", "video": "MP4", "audio": "WAV"}[kind]
    blob = f"PATI SIMULATED {kind.upper()} FILE (deterministic placeholder {label})".encode() * 64
    artifacts = [{
        "name": f"simulated_{kind}_{int(time.time())}.{label.lower()}",
        "type": kind, "mime": {"image": "image/png", "video": "video/mp4",
                               "audio": "audio/wav"}[kind],
        "path_ref": None, "inline": blob,
    }]
    # inline artifacts are uploaded by complete_job via temp file; write it
    import tempfile, os
    tmpdir = tempfile.mkdtemp(prefix="pati-sim-")
    p = Path(tmpdir) / artifacts[0]["name"]
    p.write_bytes(blob)
    artifacts[0]["path"] = str(p)
    artifacts[0]["size"] = len(blob)
    return {"simulated": True, "kind": kind, "artifacts": artifacts}
