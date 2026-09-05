"""Multipurpose capability demo: text, image, video, voice, music, research,
filesystem - everything through one $0 API.

Run:  python examples/multipurpose_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

os.environ.setdefault("PATI_DATA_DIR", tempfile.mkdtemp(prefix="pati-multi-"))
os.environ.setdefault("PATI_RATE_LIMIT_PER_MIN", "100000")

import uvicorn  # noqa: E402

from pati import PatiClient  # noqa: E402
from pati_api.app import app  # noqa: E402
from pati_api import db, security  # noqa: E402

from pati_agent.agent import PatiAgent  # noqa: E402
from pati_agent.api_client import AgentAPI  # noqa: E402
from pati_agent.audit import AuditLog  # noqa: E402
from pati_agent.config import AgentConfig  # noqa: E402
from pati_agent.policy import DEFAULT_PERMISSIONS  # noqa: E402

from conftest import MockGPUWorker  # noqa: E402


import faulthandler
def main() -> None:
    faulthandler.dump_traceback_later(75, file=open("/tmp/pati_multi_dump.txt", "w"))
    print("PATI MULTIPURPOSE DEMO - one free API, every modality")
    db.reset_db(); db.init_db()
    tok = security.bootstrap_admin_token()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}"
    admin = PatiClient(base, token=tok)
    # raise the concurrency quota for the demo (admin operation, still $0)
    admin._request("POST", "/admin/quotas/max_concurrent_tasks", json={"value": 8})

    ws = Path(tempfile.mkdtemp(prefix="pati-multi-ws-"))
    probe = AgentConfig(allowed_roots=[str(ws)], permissions=list(DEFAULT_PERMISSIONS))
    reg = admin.register_worker(name="multi-pc", wtype="LOCAL_WORKER",
                                capabilities=probe.policy_engine().capabilities())
    agent = PatiAgent(AgentConfig(server_url=base, worker_id=reg["worker_id"],
                                  token=reg["token"], worker_name="multi-pc",
                                  allowed_roots=[str(ws)],
                                  permissions=list(DEFAULT_PERMISSIONS),
                                  heartbeat_interval_s=3),
                      AuditLog(ws / "audit.jsonl"), AgentAPI(base, reg["token"]))
    agent.start()
    gpu = MockGPUWorker(base, admin, name="free-gpu")
    gpu.start()

    objectives = [
        ("text_generation", "Write a short bedtime story about a robot"),
        ("image_generation", "Generate an image of a sunrise over mountains",
         {"prompts": ["sunrise over mountains, wide shot", "close-up of dew on leaves"]}),
        ("voice_generation", "Speak this line warmly: good morning"),
        ("music_generation", "Make a cheerful background track"),
        ("research", "What is PATI and why is it free?",
         {"mode": "local_corpus", "save_to": str(ws / "Reports" / "pati_report.md")}),
        ("filesystem_organize", "Create a folder called Demo Project and organize my files",
         {"workspace": str(ws)}),
    ]
    tasks = []
    for entry in objectives:
        ttype = entry[0]
        obj = entry[1]
        params = entry[2] if len(entry) > 2 else {}
        t = admin.submit_task(obj, task_type=ttype, params=params)
        tasks.append(t)
        print(f"  submitted [{ttype:<20}] {obj[:52]:<54} -> {t['id']}")

    print("\nwaiting for all tasks...\n")
    for t in tasks:
        print(f"  ... waiting for {t['type']} ({t['id']})", flush=True)
        done = admin.wait_for_task(t["id"], timeout_s=240, poll_s=0.5)
        arts = admin.list_task_artifacts(t["id"])
        sizes = ", ".join(f"{a['name']}({a['size']}B)" for a in arts) or "-"
        print(f"  {done['status']:<10} {t['type']:<20} artifacts: {sizes}")

    print(f"\nworkspace contents after demo:")
    for p in sorted(ws.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(ws)}  ({p.stat().st_size} B)")

    agent.stop(); gpu.stop(); srv.should_exit = True
    print("\nAll modalities executed on free infrastructure. COST = $0")


if __name__ == "__main__":
    main()
