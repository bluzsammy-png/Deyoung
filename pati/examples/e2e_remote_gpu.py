"""PROOF OF FLOW 2 - free remote GPU worker (Kaggle-class) executing a job.

    Personal AI client -> PATI -> task -> REMOTE FREE WORKER ->
    artifacts uploaded -> PATI -> final artifact saved to the Local Agent's
    authorized folder -> client

The remote worker in this demo is a real HTTP pull-worker (the same protocol
a Kaggle kernel runner uses). Inference is deterministic and clearly labeled
simulated; point `pati_workers.KaggleWorker` at a free Kaggle account
(kaggle.json) to run the identical flow on genuine free GPU.

Run:  python examples/e2e_remote_gpu.py
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

os.environ.setdefault("PATI_DATA_DIR", tempfile.mkdtemp(prefix="pati-gpu-demo-"))
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

from conftest import MockGPUWorker  # noqa: E402  (test double = real HTTP worker)


def banner(msg: str) -> None:
    print(f"\n{'=' * 66}\n  {msg}\n{'=' * 66}")


def main() -> None:
    banner("PATI E2E DEMO - free GPU worker runs a video pipeline; artifacts land on disk")

    db.reset_db(); db.init_db()
    admin_token = security.bootstrap_admin_token()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}"
    admin = PatiClient(base, token=admin_token)
    print(f"[1] PATI control plane at {base}")

    # Local Agent owns an authorized folder (receives the final video)
    ws_root = Path(tempfile.mkdtemp(prefix="pati-gpu-demo-pc-"))
    ws = ws_root / "PATI workspace"
    ws.mkdir()
    probe = AgentConfig(allowed_roots=[str(ws)], permissions=list(DEFAULT_PERMISSIONS))
    reg = admin.register_worker(name="demo-pc", wtype="LOCAL_WORKER",
                                capabilities=probe.policy_engine().capabilities())
    agent = PatiAgent(AgentConfig(server_url=base, worker_id=reg["worker_id"],
                                  token=reg["token"], worker_name="demo-pc",
                                  allowed_roots=[str(ws)],
                                  permissions=list(DEFAULT_PERMISSIONS),
                                  heartbeat_interval_s=3),
                      AuditLog(ws_root / "audit.jsonl"), AgentAPI(base, reg["token"]))
    agent.start()
    print(f"[2] Local Agent online; authorized folder: {ws}")

    # Remote FREE GPU worker registers (Kaggle-class; FREE_WITH_LIMITS)
    gpu = MockGPUWorker(base, admin, name="kaggle-gpu-01")
    gpu.start()
    print(f"[3] Remote free GPU worker registered: kaggle-gpu-01 "
          f"(caps: {', '.join(list(MockGPUWorker.CAPS)[:4])} ...)")

    banner('Personal AI says: "Create a 60-second animated story and save the '
           'final video into my workspace"')
    final_path = ws / "Video Projects" / "final_video.mp4"
    task = admin.submit_task(
        "Create a 60-second animated story",
        task_type="video_workflow",
        params={"scenes": 3, "save_to": str(final_path)})
    print(f"[4] Task {task['id']} planned with {len(task['stages'])} stages:")
    for s in task["stages"]:
        par = f"  [parallel group: {s['group']}]" if s.get("group") else ""
        deps = f"  (after {', '.join(s['depends_on'])})" if s["depends_on"] else ""
        print(f"      {s['seq']:>2}. {s['name']:<18} cap={s['capability']}{par}{deps}")

    print("[5] Executing (story -> script -> bible -> storyboard -> scenes(parallel) "
          "-> voice+music -> edit -> QA -> final -> save-to-disk) ...")
    done = admin.wait_for_task(task["id"], timeout_s=180, poll_s=0.5,
                               on_log=lambda e: print(f"      [{e['level']}] {e['message']}"))
    print(f"[6] Task finished: {done['status']}")

    arts = admin.list_task_artifacts(task["id"])
    stored = [a for a in arts if a["storage"] == "control_plane"]
    print(f"[7] Artifacts produced by the free GPU worker: {len(stored)}")
    for a in stored:
        print(f"      {a['name']}  ({a['size']} B, sha256={a['checksum'][:12]}...)")
    print(f"[8] Final video saved by the Local Agent into the authorized folder:")
    print(f"      {final_path}  exists={final_path.exists()} "
          f"size={final_path.stat().st_size if final_path.exists() else 0} B")
    print(f"[9] GPU stages executed by remote worker: {gpu.executed}")

    agent.stop()
    gpu.stop()
    srv.should_exit = True

    assert done["status"] == "COMPLETED"
    assert final_path.exists()
    assert len(stored) >= 3
    print("\nDEMO RESULT: FLOW 2 PROVEN END-TO-END "
          "(client -> PATI -> free GPU worker -> artifacts -> Local Agent disk -> client)")


if __name__ == "__main__":
    main()
