"""`pati-agent doctor`: end-to-end health checks with actionable fixes."""
from __future__ import annotations

import os
import pathlib
import sys
from pathlib import Path

from .api_client import AgentAPI
from .config import AgentConfig


def run_doctor() -> int:
    cfg_path = Path.home() / ("PATI/agent/config.json" if os.name == "nt"
                              else ".pati/agent/config.json")
    failures = 0

    def check(name: str, ok: bool, fix: str = ""):
        nonlocal failures
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f"  -> fix: {fix}" if not ok and fix else ""))
        if not ok:
            failures += 1

    print("PATI Local Agent diagnostics")
    print("-" * 50)

    check("config file exists", cfg_path.exists(), "run: pati-agent setup")
    if not cfg_path.exists():
        return 1
    cfg = AgentConfig.load(cfg_path)

    api = AgentAPI(cfg.server_url, cfg.token)
    try:
        h = api.health()
        check(f"control plane reachable ({cfg.server_url})", h.get("status") == "ok",
              f"start the control plane: pati-server")
    except Exception as e:
        check(f"control plane reachable ({cfg.server_url})", False, f"start pati-server ({e})")
        return 1

    try:
        api.heartbeat(cfg.worker_id, {"doctor": True})
        check("worker token valid + heartbeat accepted", True)
    except Exception as e:
        check("worker token valid + heartbeat accepted", False,
              "re-run: pati-agent setup (issue a fresh pairing code with: pati admin-pair)")

    check("at least one authorized folder", bool(cfg.allowed_roots),
          "pati-agent authorize-folder add <directory>")
    for r in cfg.allowed_roots:
        p = pathlib.Path(r)
        check(f"folder exists: {r}", p.exists(), f"create it or remove: pati-agent authorize-folder remove {r}")
        if p.exists():
            probe = p / "_pati_doctor_probe"
            try:
                probe.write_text("x")
                probe.unlink()
                check(f"folder writable: {r}", True)
            except OSError:
                check(f"folder writable: {r}", False, "check folder permissions")

    danger = [p for p in cfg.permissions if p in ("DELETE_FILES", "EXECUTE_COMMANDS", "RUN_SCRIPTS")]
    if danger:
        print(f"[WARN] dangerous permissions enabled: {danger} (intentional?)")

    from .audit import AuditLog
    audit = AuditLog(Path.home() / ("PATI/agent/audit.jsonl" if os.name == "nt"
                                    else ".pati/agent/audit.jsonl"))
    ok, n = audit.verify()
    check(f"audit chain integrity ({n} records)", ok, "inspect audit.jsonl for tampering")

    print("-" * 50)
    print("RESULT:", "ALL CHECKS PASSED" if failures == 0 else f"{failures} check(s) failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run_doctor())
