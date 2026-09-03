"""`pati-agent update`: free-channel update check (PyPI / local wheel).

The updater NEVER executes downloaded code silently and NEVER uses paid
distribution channels. It reports the manifest from the control plane and
performs a plain `pip install --upgrade pati` when --yes is passed.
"""
from __future__ import annotations

import subprocess
import sys

from .api_client import AgentAPI
from .config import AgentConfig


def load_cfg():
    import os
    from pathlib import Path
    p = Path.home() / ("PATI/agent/config.json" if os.name == "nt"
                       else ".pati/agent/config.json")
    if not p.exists():
        print("no agent config; run: pati-agent setup")
        sys.exit(1)
    return AgentConfig.load(p)


def check_updates(apply: bool = False) -> int:
    cfg = load_cfg()
    api = AgentAPI(cfg.server_url, cfg.token)
    manifest = api._http.get("/api/v1/system/updates").json()
    print(f"current version: {manifest['current_version']}")
    print(f"latest version:  {manifest['latest_version']}")
    print(f"channel:         {manifest['channel']} (free channels only)")
    if manifest["current_version"] == manifest["latest_version"]:
        print("up to date")
        return 0
    print("update method:", manifest["method"])
    if apply:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pati"]
        print("running:", " ".join(cmd))
        return subprocess.call(cmd)
    print("(dry run; pass --yes to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(check_updates(apply="--yes" in sys.argv))
