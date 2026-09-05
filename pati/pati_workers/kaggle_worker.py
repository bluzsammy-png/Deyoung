"""Kaggle GPU worker - legitimate free batch compute (FREE_WITH_LIMITS).

Researched 2026-09-02 (see docs/RESEARCH_REPORT.md):
- Official API: https://www.kaggle.com/docs/api  (kaggle CLI + public API,
  dynamic rate limits; token the USER creates for free).
- Free GPU quota is ~30 hours/week (Kaggle announcement "Weekly Maximum GPU
  Usage"), sessions are capped (<=12h) and kernels run in ephemeral sandboxes.
- Kaggle is EPHEMERAL BATCH COMPUTE, never a permanent server. PATI quota
  manager additionally budgets GPU minutes locally so the weekly allowance
  is spent deliberately.

Credentials (both official styles accepted, checked in this order):
1. KAGGLE_API_TOKEN environment variable (new KGAT_* tokens).
2. ~/.kaggle/access_token file (new-style token; what Kaggle's site
   currently hands out - one token string per line, nothing else).
3. ~/.kaggle/kaggle.json (classic {"username": ..., "key": ...} file;
   also lets us resolve the username for kernel slugs locally).

Design:
- Kernels are pushed with `kaggle kernels push`, status via
  `kaggle kernels status`, outputs via `kaggle kernels output` (all free).
- Open-weights models are attached from Kaggle Models (hosted by Kaggle -
  no bandwidth cost, no license violation: weights stay in Kaggle's infra).
- When no credential is present the worker reports unavailable and the
  router returns RESOURCE_UNAVAILABLE - never a paid fallback.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .interface import UniversalWorkerInterface


class KaggleNotConfigured(Exception):
    """Raised when no free Kaggle credentials exist on this machine."""


def _read_access_token() -> str | None:
    """New-style token: env var first, then ~/.kaggle/access_token file."""
    env_tok = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if env_tok:
        return env_tok
    f = Path.home() / ".kaggle" / "access_token"
    try:
        tok = f.read_text(encoding="utf-8").strip()
        return tok or None
    except OSError:
        return None


def kaggle_credentials() -> dict:
    """Report which official credential style is configured (no secrets)."""
    if shutil.which("kaggle") is None:
        return {"ok": False, "reason": "kaggle CLI not installed (pip install kaggle)"}
    if _read_access_token():
        return {"ok": True, "style": "access_token",
                "source": "env" if os.environ.get("KAGGLE_API_TOKEN") else str(Path.home() / ".kaggle" / "access_token")}
    if (Path.home() / ".kaggle" / "kaggle.json").exists():
        return {"ok": True, "style": "kaggle.json",
                "source": str(Path.home() / ".kaggle" / "kaggle.json")}
    return {"ok": False, "reason": "no Kaggle token found"}


def kaggle_available() -> bool:
    return kaggle_credentials()["ok"]


def cli_env() -> dict:
    """Environment for kaggle CLI subprocesses.

    Ensures KAGGLE_API_TOKEN is present for new-style tokens so the CLI
    picks credentials up even when the env var was not exported globally.
    """
    env = dict(os.environ)
    tok = _read_access_token()
    if tok:
        env["KAGGLE_API_TOKEN"] = tok
    return env


KERNEL_TEMPLATE = """
# PATI Kaggle job (generated). Free-tier batch compute; ephemeral by design.
import json, os, sys
inputs = json.loads(r'''{inputs_json}''')

def main():
{body}

if __name__ == "__main__":
    main()
"""


class KaggleWorker(UniversalWorkerInterface):
    """Push-style worker: submits kernels to Kaggle's free GPU pool.

    capability -> kernel body mapping is pluggable (see adapters). The
    default text generation kernel attaches an open-weights instruct model
    via Kaggle Models and writes the result to /kaggle/working.
    """

    def __init__(self, slug_prefix: str = "pati", quota_gpu_minutes_per_day: int = 240):
        self.slug_prefix = slug_prefix
        self.quota_gpu_minutes_per_day = quota_gpu_minutes_per_day
        self._usage_minutes = 0.0
        self._jobs: dict[str, dict] = {}

    # ------------------------------------------------------------------ meta
    def register(self) -> dict:
        creds = kaggle_credentials()
        if not creds["ok"]:
            return {"status": "unavailable", "reason": creds.get("reason", "no credentials"),
                    "remedy": "free account -> kaggle.com -> Settings -> API -> Create New Token; "
                              "put it at ~/.kaggle/access_token (new style) or ~/.kaggle/kaggle.json (classic); "
                              "pip install kaggle"}
        return {"status": "available", "type": "KAGGLE_WORKER",
                "free_status": "FREE_WITH_LIMITS", "credential_style": creds["style"]}

    def health(self) -> dict:
        return {"ok": kaggle_available(), "kind": "KAGGLE_WORKER"}

    def capabilities(self) -> list[str]:
        return ["text_generation", "image_generation", "text_to_video", "text_to_speech",
                "speech_to_text", "music_generation", "GPU_execution", "coding",
                "structured_output", "summarization", "reasoning"]

    def resources(self) -> dict:
        return {"gpu": "Kaggle free T4/P100 (quota ~30h/week)", "gpu_minutes_left_today":
                max(0, self.quota_gpu_minutes_per_day - int(self._usage_minutes))}

    def heartbeat(self) -> dict:
        return {"ok": True, "resources": self.resources()}

    def shutdown(self) -> dict:
        return {"ok": True}

    # ----------------------------------------------------------------- jobs
    def submit(self, job: dict) -> dict:
        if not kaggle_available():
            raise KaggleNotConfigured(
                "RESOURCE_UNAVAILABLE: no free Kaggle credentials configured")
        est = float(job.get("params", {}).get("estimated_gpu_minutes", 2))
        if self._usage_minutes + est > self.quota_gpu_minutes_per_day:
            raise KaggleNotConfigured(
                "RESOURCE_UNAVAILABLE: local GPU-minute budget exhausted for today")
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        kernel_slug = f"pati-{job_id.lower()}"
        workdir = Path(tempfile.mkdtemp(prefix="pati-kaggle-"))
        body = self._kernel_body(job)
        meta = self._kernel_meta(kernel_slug, job)
        (workdir / "pati_job.py").write_text(body)
        (workdir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
        # kaggle CLI is the official, free automation path
        proc = subprocess.run(["kaggle", "kernels", "push", "-p", str(workdir)],
                              capture_output=True, text=True, timeout=120, env=cli_env())
        self._jobs[job_id] = {"slug": f"{meta['id']}", "dir": str(workdir),
                              "submitted_at": time.time(), "est_minutes": est,
                              "push_stdout": proc.stdout[-2000:], "push_stderr": proc.stderr[-2000:]}
        if proc.returncode != 0:
            return {"job_id": job_id, "status": "FAILED",
                    "error": f"kaggle push failed: {proc.stderr[-500:]}"}
        self._usage_minutes += est
        return {"job_id": job_id, "status": "SUBMITTED", "kernel": meta["id"]}

    def status(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "UNKNOWN"}
        proc = subprocess.run(["kaggle", "kernels", "status", job["slug"]],
                              capture_output=True, text=True, timeout=60, env=cli_env())
        out = (proc.stdout + proc.stderr).lower()
        if "complete" in out:
            return {"job_id": job_id, "status": "COMPLETE"}
        if "error" in out or "cancel" in out:
            return {"job_id": job_id, "status": "FAILED", "error": out[-500:]}
        return {"job_id": job_id, "status": "RUNNING"}

    def cancel(self, job_id: str) -> dict:
        # Kaggle kernels cannot be cancelled via the public API; we simply
        # stop tracking and stop consuming their outputs.
        self._jobs.pop(job_id, None)
        return {"ok": True, "note": "kernel left to finish; outputs discarded"}

    def logs(self, job_id: str) -> list[dict]:
        job = self._jobs.get(job_id)
        if not job:
            return []
        proc = subprocess.run(["kaggle", "kernels", "output", job["slug"], "-p", job["dir"]],
                              capture_output=True, text=True, timeout=300, env=cli_env())
        log_file = Path(job["dir"]) / "pati_job.log"
        if log_file.exists():
            return [{"level": "info", "message": log_file.read_text(errors="replace")[-5000:]}]
        return [{"level": "info", "message": (proc.stdout + proc.stderr)[-5000:]}]

    def artifacts(self, job_id: str) -> list[dict]:
        job = self._jobs.get(job_id)
        if not job:
            return []
        out_dir = Path(job["dir"]) / "output"
        out_dir.mkdir(exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", job["slug"], "-p", str(out_dir)],
                       capture_output=True, text=True, timeout=300, env=cli_env())
        return [{"name": p.name, "path": str(p), "size": p.stat().st_size}
                for p in out_dir.rglob("*") if p.is_file()]

    # ------------------------------------------------------------------ body
    def _kernel_body(self, job: dict) -> str:
        capability = job.get("capability", "text_generation")
        params = json.dumps(job.get("params", {}))
        if capability in ("text_generation", "summarization", "structured_output",
                          "reasoning", "research_synthesis", "coding", "code_generation"):
            body = f"""
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    model_id = os.environ.get("PATI_KAGGLE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")
    prompt = inputs.get("prompt", "")
    ids = tok.apply_chat_template([{{"role":"user","content":prompt}}], add_generation_prompt=True, return_tensors="pt").to(model.device)
    out = model.generate(ids, max_new_tokens=int(inputs.get("max_new_tokens", 700)))
    text = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    with open("/kaggle/working/result.json", "w") as f:
        json.dump({{"text": text, "model": model_id, "simulated": False}}, f)
"""
        elif capability == "image_generation":
            body = f"""
    from diffusers import StableDiffusionXLPipeline
    import torch
    pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, variant="fp16").to("cuda")
    img = pipe(inputs.get("prompt", ""), num_inference_steps=30).images[0]
    img.save("/kaggle/working/result.png")
    with open("/kaggle/working/result.json", "w") as f:
        json.dump({{"image": "result.png", "simulated": False}}, f)
"""
        else:
            body = f"""
    with open("/kaggle/working/result.json", "w") as f:
        json.dump({{"ok": False, "error": "capability not yet mapped in kaggle adapter", "capability": "{capability}"}}, f)
"""
        return KERNEL_TEMPLATE.format(inputs_json=params.replace("'''", "''' "), body=body)

    def _kernel_meta(self, slug: str, job: dict) -> dict:
        kaggle_user = self._kaggle_user()
        return {
            "id": f"{kaggle_user}/{slug}",
            "title": slug.replace("-", " ").title(),
            "code_file": "pati_job.py",
            "language": "python",
            "kernel_type": "script",
            "enable_gpu": "true",
            "enable_internet": job.get("params", {}).get("enable_internet", False),
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": job.get("params", {}).get("model_sources", []),
        }

    _username_cache: str | None = None

    @classmethod
    def _kaggle_user(cls) -> str:
        """Best-effort username for kernel slugs.

        Order: kaggle.json (has it in plaintext) -> KAGGLE_USERNAME env ->
        `kaggle config view` (works with new-style tokens, cached) ->
        neutral fallback (push will fail with a clear CLI error).
        """
        if cls._username_cache:
            return cls._username_cache
        user = None
        try:
            user = json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())["username"]
        except Exception:
            pass
        if not user:
            user = os.environ.get("KAGGLE_USERNAME", "").strip() or None
        if not user:
            try:
                proc = subprocess.run(["kaggle", "config", "view"], capture_output=True,
                                      text=True, timeout=30, env=cli_env())
                for line in (proc.stdout + proc.stderr).splitlines():
                    if "user_name" in line.lower() and ":" in line:
                        cand = line.split(":", 1)[1].strip()
                        if cand:
                            user = cand
                            break
            except Exception:
                pass
        cls._username_cache = user or "pati-user"
        return cls._username_cache


# ---------------------------------------------------------------------------
# Container worker (optional, free via local Docker; skipped when absent)
# ---------------------------------------------------------------------------
class ContainerWorker:
    def __init__(self):
        self.docker = shutil.which("docker") is not None

    def register(self) -> dict:
        return {"status": "available" if self.docker else "unavailable (docker not found)",
                "type": "CONTAINER_WORKER"}

    def capabilities(self) -> list[str]:
        return ["container_execution", "coding", "batch_execution"] if self.docker else []

    def health(self) -> dict:
        return {"ok": self.docker}
