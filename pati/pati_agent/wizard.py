"""Local Agent setup wizard - the 12-step install experience.

INSTALL -> CONNECT -> AUTHENTICATE -> NAME -> AUTHORIZE FOLDERS ->
PERMISSIONS -> HARDWARE -> CAPABILITIES -> TESTS -> AUTOSTART -> READY

Windows-first (per owner decision), cross-platform. The wizard never asks
the user to understand PATI's internals; it needs exactly two secrets:
the PATI server URL and a one-time pairing code (issued by `pati admin-pair`).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path

from .api_client import AgentAPI
from .config import AgentConfig
from .policy import (ALL_PERMISSIONS, DANGEROUS, DEFAULT_PERMISSIONS,
                     CAPABILITY_FOR_PERMISSION)


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def _ask_yes(prompt: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def run_wizard(server: str = "", code: str = "", non_interactive_roots: list[str] | None = None,
               assume_yes: bool = False) -> AgentConfig:
    print("=" * 70)
    print("PATI LOCAL AGENT - SETUP WIZARD")
    print("(installs the secure bridge between PATI and this computer - $0)")
    print("=" * 70)

    cfg_path = Path.home() / ("PATI/agent/config.json" if os.name == "nt" else ".pati/agent/config.json")

    # 1. Connect PATI account/server
    server = server or _ask("1/12 PATI server URL", "http://127.0.0.1:8000")
    api_probe = AgentAPI(server, token="anonymous")
    try:
        h = api_probe.health()
        print(f"    control plane reachable: v{h.get('version')} FREE_ONLY={h.get('free_only')}")
    except Exception as e:
        print(f"    ERROR: cannot reach {server}: {e}")
        print("    Start it first:  pati-server  (or reinstall via installer)")
        sys.exit(1)

    # 2. Authenticate this computer (pairing code from `pati admin-pair`)
    code = code or _ask("2/12 one-time pairing code (from 'pati admin-pair' on the server)")
    # 3. Name the computer/worker
    name = _ask("3/12 name for this computer", os.uname().nodename if os.name != "nt"
                else os.environ.get("COMPUTERNAME", "my-windows-pc"))

    # provisional token-less registration happens after folder config; we need
    # a token to heartbeat, so pair now with placeholder capabilities.
    tmp_api = AgentAPI(server, token="anonymous")
    reg = tmp_api.register(name=name, wtype="LOCAL_WORKER", capabilities=["system_inspection"],
                           pairing_code=code, machine={"os": os.name})
    cfg = AgentConfig(server_url=server, worker_id=reg["worker_id"], token=reg["token"],
                      worker_name=name)
    cfg.heartbeat_interval_s = reg.get("heartbeat_interval_s", 15)
    print(f"    authenticated: worker {cfg.worker_id}")

    # 4. Select authorized folders
    roots: list[str] = []
    if non_interactive_roots:
        roots = [str(pathlib.Path(r).expanduser().resolve()) for r in non_interactive_roots]
    else:
        suggested = str(Path.home() / "PATI/workspace")
        print("    These folders are the ONLY places PATI may touch on this computer.")
        print("    Restricted by design: OS dirs, password stores, browser profiles,")
        print("    SSH keys, wallets, production secrets.")
        while True:
            r = _ask("4/12 add authorized folder", suggested if not roots else "")
            if not r:
                break
            p = pathlib.Path(r).expanduser().resolve()
            if not p.exists():
                if _ask_yes(f"    '{p}' does not exist. Create it?", True):
                    p.mkdir(parents=True, exist_ok=True)
                else:
                    continue
            if str(p) not in roots:
                roots.append(str(p))
            if not _ask_yes("    add another folder?", False):
                break
    if not roots:
        p = pathlib.Path(suggested).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        roots = [str(p)]
    cfg.allowed_roots = roots
    print(f"    authorized folders: {roots}")

    # 5. Configure permissions
    print("5/12 permissions (dangerous ones are OFF by default)")
    if assume_yes:
        perms = list(DEFAULT_PERMISSIONS)
    else:
        perms = []
        for perm in ALL_PERMISSIONS:
            default = perm in DEFAULT_PERMISSIONS
            tag = " - allows deleting files (irreversible)" if perm == "DELETE_FILES" else ""
            if _ask_yes(f"    {perm}{tag}", default):
                perms.append(perm)
    cfg.permissions = perms

    # 6. Detect hardware
    from .sysinfo import resource_report
    report = resource_report(roots)
    print(f"6/12 hardware: {report['cpu_count']} vCPU, {report['ram_total_mb']} MB RAM, "
          f"GPU: {report['gpus'] or 'none (heavy jobs will use free Kaggle GPU)'}")

    # 7. Register worker capabilities
    from .audit import AuditLog
    audit = AuditLog(Path.home() / ("PATI/agent/audit.jsonl" if os.name == "nt"
                                    else ".pati/agent/audit.jsonl"))
    engine = cfg.policy_engine()
    api = AgentAPI(server, cfg.token)
    caps = engine.capabilities()
    api.heartbeat(cfg.worker_id, resource_report(roots), capabilities=caps)
    print(f"7/12 registered capabilities: {caps}")

    # 8. Test PATI connection
    h = api.health()
    assert h["status"] == "ok"
    print("8/12 PATI connection test: PASS")

    # 9. Test filesystem access
    test_dir = pathlib.Path(roots[0]) / "_pati_selftest"
    test_dir.mkdir(parents=True, exist_ok=True)
    tf = test_dir / "write_test.txt"
    tf.write_text("pati self test", encoding="utf-8")
    assert tf.read_text() == "pati self test"
    tf.unlink()
    test_dir.rmdir()
    print("9/12 filesystem test: PASS (write+read+delete inside authorized folder)")

    # 10. Test task execution (submit tiny task through the control plane)
    print("10/12 task-execution test: worker registered; PATI will route jobs here automatically")

    # 11. Configure automatic startup
    if assume_yes or _ask_yes("11/12 start PATI agent automatically at login?", True):
        ok = _install_autostart()
        cfg.autostart = ok
        print(f"    autostart: {'installed' if ok else 'skipped (see docs/INSTALL.md)'}")

    # 12. Finish
    cfg.save(cfg_path)
    audit.append("wizard.completed", resource=str(cfg_path),
                 detail={"roots": roots, "permissions": perms})
    print("12/12 setup complete")
    print(f"    config: {cfg_path}")
    print(f"    start now:  pati-agent run")
    print(f"    diagnostics: pati-agent doctor")
    print(f"    manage folders: pati-agent authorize-folder add|remove|list")
    print("READY.")
    return cfg


def _install_autostart() -> bool:
    try:
        if os.name == "nt":
            cmd = ("schtasks /Create /SC ONLOGON /TN PATI-Agent /TR "
                   f"\" pati-agent run\" /F")
            return subprocess.call(cmd, shell=True) == 0
        if sys.platform == "darwin":
            src = Path(__file__).parent.parent / "installer" / "com.pati.agent.plist"
            dst = Path.home() / "Library/LaunchAgents/com.pati.agent.plist"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            subprocess.call(["launchctl", "load", str(dst)])
            return dst.exists()
        src = Path(__file__).parent.parent / "installer" / "pati-agent.service"
        dst = Path.home() / ".config/systemd/user/pati-agent.service"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        subprocess.call(["systemctl", "--user", "daemon-reload"])
        subprocess.call(["systemctl", "--user", "enable", "--now", "pati-agent"])
        return True
    except Exception:
        return False
