"""Sandboxed command/script execution for the Local Agent.

- EXECUTE_COMMANDS / RUN_SCRIPTS are disabled by default and must be granted
  explicitly by the owner.
- Commands must appear verbatim in the configured allowlist (basenames).
- POSIX: CPU/memory/file-size/process limits via resource rlimits in a
  preexec hook; hard timeout with process-group kill.
- Windows: timeout + allowlist enforced; Job Objects noted in docs
  (SANDBOX_SPEC.md) as the hardening path.
- Environment is scrubbed; no shell interpolation; argv array only.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time

from .policy import EXECUTE_COMMANDS, RUN_SCRIPTS, PolicyViolation

_BLOCKED_ENV_PREFIXES = ("PATI_TOKEN", "AWS_", "GOOGLE_", "KAGGLE_", "GITHUB_TOKEN")


def _clean_env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if not any(k.startswith(p) for p in _BLOCKED_ENV_PREFIXES)}
    env["PATH"] = os.environ.get("PATH", os.defpath)
    return env


def _posix_limits(cpu_s: int, mem_mb: int, fsize_mb: int):
    def hook():  # pragma: no cover - runs in child
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_mb * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        os.setsid()
    return hook if os.name == "posix" else None


class ExecOperations:
    def __init__(self, engine, audit_log):
        self.engine = engine
        self.audit = audit_log

    def run_command(self, params: dict) -> dict:
        self.engine.require(EXECUTE_COMMANDS)
        argv = [str(a) for a in (params.get("argv") or [])]
        self.engine.validate_command(argv)
        cwd = params.get("cwd")
        if cwd:
            cwd_path = self.engine.validate_path(cwd, params.get("root"))
            if not cwd_path.is_dir():
                raise PolicyViolation("cwd is not a directory")
            cwd = str(cwd_path)
        timeout = min(int(params.get("timeout_s", 120)), 1800)
        mem_mb = min(int(params.get("mem_limit_mb", 1024)), 4096)
        self.audit.append("command.run", resource=argv[0], detail={"argv": argv, "timeout": timeout})
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                argv, cwd=cwd, env=_clean_env(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=_posix_limits(cpu_s=timeout, mem_mb=mem_mb, fsize_mb=256))
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill_tree(proc)
                out, err = b"", b"timed out"
                return_code = -9
            else:
                return_code = proc.returncode
        except FileNotFoundError:
            return {"returncode": 127, "stdout": "", "stderr": f"command not found: {argv[0]}",
                    "duration_s": 0}
        return {"returncode": return_code,
                "stdout": out.decode("utf-8", "replace")[-20000:],
                "stderr": err.decode("utf-8", "replace")[-20000:],
                "duration_s": round(time.time() - t0, 2)}

    def run_script(self, params: dict) -> dict:
        self.engine.require(RUN_SCRIPTS)
        root = self.engine.resolve_root(params.get("root"))
        script = self.engine.validate_path(params["path"], params.get("root"), must_exist=True)
        try:
            script.relative_to(root)
        except ValueError:
            raise PolicyViolation("scripts must live inside an authorized folder")
        interpreter = params.get("interpreter")
        if not interpreter:
            ext_map = {".py": "python3", ".sh": "bash", ".ps1": "powershell",
                       ".js": "node", ".bat": "cmd"}
            interpreter = ext_map.get(script.suffix.lower())
            if not interpreter:
                raise PolicyViolation(f"no interpreter mapping for {script.suffix}")
        argv = [interpreter, str(script)] + [str(a) for a in (params.get("args") or [])]
        return self.run_command({"argv": argv, "cwd": params.get("cwd"),
                                 "root": params.get("root"),
                                 "timeout_s": params.get("timeout_s", 300),
                                 "mem_limit_mb": params.get("mem_limit_mb", 1024)})

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _kill_tree(proc: subprocess.Popen) -> None:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError, OSError):
            pass
