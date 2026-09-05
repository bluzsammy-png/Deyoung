"""PROOF OF FLOW 1 - hard-drive automation through the Local Agent.

    Personal AI client -> PATI -> task -> Local Agent ->
    authorized hard-drive operation -> artifact/result -> PATI -> client

Run:  python examples/e2e_demo.py
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

os.environ.setdefault("PATI_DATA_DIR", tempfile.mkdtemp(prefix="pati-demo-"))
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


def banner(msg: str) -> None:
    print(f"\n{'=' * 66}\n  {msg}\n{'=' * 66}")


def main() -> None:
    banner("PATI E2E DEMO - Personal AI asks PATI to organize the hard drive")

    # 1. Start the control plane (on your PC this is `pati-server`)
    db.reset_db(); db.init_db()
    admin_token = security.bootstrap_admin_token()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}"
    print(f"[1] PATI control plane running at {base}  (FREE_ONLY=true, MAX_SPEND=0)")

    admin = PatiClient(base, token=admin_token)

    # 2. Simulate the user's hard drive: a workspace with today's media
    ws_root = Path(tempfile.mkdtemp(prefix="pati-demo-pc-"))
    ws = ws_root / "Video Projects"
    ws.mkdir()
    (ws / "script.txt").write_text("Episode 1: PATI takes over the world (of chores)")
    (ws / "thumbnail.png").write_bytes(b"\x89PNG fake-image-bytes")
    (ws / "voiceover.wav").write_bytes(b"fake-audio-bytes")
    (ws / "final-cut.mp4").write_bytes(b"fake-video-bytes")
    print(f"[2] Hard-drive workspace prepared: {ws}")
    print("    script.txt, thumbnail.png, voiceover.wav, final-cut.mp4")

    # 3. Install + start the Local Agent (on your PC this is the setup wizard)
    probe = AgentConfig(allowed_roots=[str(ws)], permissions=list(DEFAULT_PERMISSIONS))
    reg = admin.register_worker(name="demo-windows-pc", wtype="LOCAL_WORKER",
                                capabilities=probe.policy_engine().capabilities())
    agent_cfg = AgentConfig(server_url=base, worker_id=reg["worker_id"], token=reg["token"],
                            worker_name="demo-windows-pc", allowed_roots=[str(ws)],
                            permissions=list(DEFAULT_PERMISSIONS), heartbeat_interval_s=3)
    audit = AuditLog(ws_root / "agent_audit.jsonl")
    agent = PatiAgent(agent_cfg, audit, AgentAPI(base, reg["token"]))
    agent.start()
    print(f"[3] Local Agent authenticated + online (worker {reg['worker_id'][:16]}...)")
    print("    authorized folders: [" + str(ws) + "]")
    print("    dangerous permissions (DELETE_FILES, EXECUTE_COMMANDS, RUN_SCRIPTS): OFF")

    # 4. The Personal AI (Z.ai or any client) submits the objective
    banner('Personal AI says: "Create a folder called YouTube Project 01 in my '
           'authorized Video Projects directory and organize today\'s files"')
    task = admin.submit_task(
        "Create a folder called YouTube Project 01 in my Video Projects folder",
        task_type="filesystem_organize", params={"workspace": str(ws)})
    print(f"[4] PATI accepted objective -> task {task['id']}")
    print("    plan: " + " -> ".join(s["name"] for s in task["stages"]))

    # 5. Watch PATI orchestrate until done
    done = admin.wait_for_task(task["id"], timeout_s=90, poll_s=0.5,
                               on_log=lambda e: print(f"      [{e['level']}] {e['message']}"))
    print(f"[5] Task finished: {done['status']}")

    # 6. Results: files on disk + artifacts recorded by PATI + audit chain
    project = ws / "YouTube Project 01"
    print(f"[6] Files on disk now:")
    for p in sorted(project.rglob("*")):
        if p.is_file():
            print(f"      {p.relative_to(ws)}")
    arts = admin.list_task_artifacts(task["id"])
    for a in arts:
        print(f"    artifact: {a['name']} ({a['size']} B, storage={a['storage']})")
    ok, n = audit.verify()
    print(f"[7] Local audit chain verified: {n} records, integrity={'OK' if ok else 'BROKEN'}")

    # 7. The Personal AI reports back to the user
    print("[8] Personal AI -> user: 'Done! Created YouTube Project 01 and organized "
          "your script, image, audio and video into subfolders.'")

    agent.stop()
    srv.should_exit = True

    assert done["status"] == "COMPLETED"
    assert (project / "scripts" / "script.txt").exists()
    print("\nDEMO RESULT: FLOW 1 PROVEN END-TO-END (client -> PATI -> Local Agent -> disk -> client)")


if __name__ == "__main__":
    main()
