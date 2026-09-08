#!/usr/bin/env python3
"""Task 55: deploy c20 worker into the prepared T4 studio.

Foreground only. Steps, each evidenced:
  1. b64-push worker code through run() -> h3work/c20_worker.py
  2. sha256 verify inside vs local
  3. launch detached inside the studio (nohup + disown)
  4. confirm first status beats
"""
import base64
import hashlib
import json
import os
import pathlib
import time

ROOT = pathlib.Path("/home/z/my-project")
LOCAL = ROOT / "campaign/site-worker/deyoung-lightning-c20.py"
KEY = json.loads((ROOT / "workers/secrets/lightning_tokens.json").read_text())["keys"][0]["key"]
os.environ["LIGHTNING_API_KEY"] = KEY

from lightning_sdk import Studio  # noqa: E402

code = LOCAL.read_bytes()
b64 = base64.b64encode(code).decode()
local_sha = hashlib.sha256(code).hexdigest()
print(f"local: {len(code)} bytes sha={local_sha[:16]} b64={len(b64)}", flush=True)

st = Studio(name="deyoung-h3", teamspace="default-project", user="deyoungsltd")
print("studio:", st.status, getattr(st, "machine", "?"), flush=True)

# 1+2: push + verify (single command; b64 has no shell metachars)
out = st.run(
    f"echo '{b64}' | base64 -d > /teamspace/studios/this_studio/h3work/c20_worker.py && "
    "sha256sum /teamspace/studios/this_studio/h3work/c20_worker.py")
remote_sha = out.strip().split()[0] if out.strip() else "none"
print("remote sha:", remote_sha[:16], "match:", remote_sha == local_sha, flush=True)
if remote_sha != local_sha:
    raise SystemExit("SHA MISMATCH - aborting launch")

# 3: launch detached
out2 = st.run(
    "cd /teamspace/studios/this_studio/h3work && "
    f"SUPA_URL='{json.loads((ROOT/'workers/secrets/supabase.json').read_text())['supabase']['supabase_url']}' "
    f"SUPA_KEY='{json.loads((ROOT/'workers/secrets/supabase.json').read_text())['supabase']['service_role_key']}' "
    "nohup python3 c20_worker.py > c20.log 2>&1 & disown; echo LAUNCHED")
print("launch:", out2.strip()[-30:], flush=True)

# 4: first beats
for i in range(6):
    time.sleep(15)
    beat = st.run("cat /teamspace/studios/this_studio/h3work/status_c20.json 2>/dev/null | head -c 400 || echo NOFILE; echo; tail -3 /teamspace/studios/this_studio/h3work/c20.log 2>/dev/null")
    print(f"--- beat {i} ---", flush=True)
    print(beat[:600], flush=True)
    if "NOFILE" not in beat and "phase" in beat:
        print("WORKER BEATING - DEPLOY OK", flush=True)
        break
