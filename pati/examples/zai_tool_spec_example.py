"""How Z.ai (or any tool-calling Personal AI) integrates with PATI - $0.

The adapter produces an OpenAI-compatible tool spec. Register it with Z.ai's
custom-tool mechanism; when Z.ai decides to call `pati_submit_objective`, the
callback runs `handle_tool_call`, which submits the objective to PATI.

Run:  python examples/zai_tool_spec_example.py
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

os.environ.setdefault("PATI_DATA_DIR", tempfile.mkdtemp(prefix="pati-zai-"))
os.environ.setdefault("PATI_RATE_LIMIT_PER_MIN", "100000")

import uvicorn  # noqa: E402
from pati import PatiClient  # noqa: E402
from pati.adapters import ZAIAdapter  # noqa: E402
from pati_api.app import app  # noqa: E402
from pati_api import db, security  # noqa: E402


def main() -> None:
    db.reset_db(); db.init_db()
    tok = security.bootstrap_admin_token()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}"

    # A dedicated client token for Z.ai (principle of least privilege)
    admin = PatiClient(base, token=tok)
    zai_token = admin.issue_token("zai-browser-client", kind="client")
    zai = PatiClient(base, token=zai_token["token"])
    adapter = ZAIAdapter(zai)

    print("1. Paste this tool spec into your Z.ai custom tools config:\n")
    print(json.dumps(adapter.tool_spec(), indent=2))

    print("\n2. When Z.ai calls a PATI tool during a conversation:")
    result = adapter.handle_tool_call("pati_submit_objective", {
        "objective": "Create a folder called Z.ai Demo in my workspace and organize my files",
        "type": "filesystem_organize",
        "params": {},
    })
    print("   Z.ai receives:", result)
    task_id = json.loads(result)["task_id"]

    print("\n3. Z.ai asks for status (pati_get_task):")
    print("   " + adapter.handle_tool_call("pati_get_task", {"task_id": task_id}))

    print("\n4. Capabilities Z.ai can announce to the user:\n")
    print(adapter.describe_capabilities())

    srv.should_exit = True
    print("\nZ.ai stays a thin client: planning, routing, execution and artifacts"
          "\nall happen inside PATI. Swap Z.ai for another AI later without "
          "touching PATI.")


if __name__ == "__main__":
    main()
