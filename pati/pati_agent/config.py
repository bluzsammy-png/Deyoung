"""Local Agent configuration (JSON file, restrictive perms on POSIX)."""
from __future__ import annotations

import json
import os
import pathlib
from dataclasses import asdict, dataclass, field

from .policy import DEFAULT_PERMISSIONS


def default_agent_dir() -> pathlib.Path:
    home = pathlib.Path.home()
    if os.name == "nt":
        return home / "PATI" / "agent"
    return home / ".pati" / "agent"


@dataclass
class AgentConfig:
    server_url: str = "http://127.0.0.1:8000"
    worker_id: str = ""
    worker_name: str = ""
    worker_type: str = "LOCAL_WORKER"
    token: str = ""
    allowed_roots: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=lambda: list(DEFAULT_PERMISSIONS))
    allowed_commands: list[str] = field(default_factory=list)
    autostart: bool = False
    heartbeat_interval_s: int = 15
    longpoll_wait_s: int = 25
    upload_threshold_mb: int = 25
    job_timeout_s: int = 1500

    # ---------------------------------------------------------------- io
    def save(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
        try:
            path.chmod(0o600)
        except OSError:
            pass

    @classmethod
    def load(cls, path: pathlib.Path) -> "AgentConfig":
        data = json.loads(pathlib.Path(path).read_text())
        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def policy_engine(self):
        from .policy import PolicyEngine
        return PolicyEngine(allowed_roots=list(self.allowed_roots),
                            permissions=list(self.permissions),
                            allowed_commands=list(self.allowed_commands))
