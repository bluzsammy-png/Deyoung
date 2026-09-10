#!/usr/bin/env python3
"""Task 61: start the deyoung-h3 studio for the tmux worker test window.

Starts the machine (T4 expected from Task 55's switch), verifies GPU attach,
records balance before/after. Foreground only, evidence to brain/lightning61_start.json.
"""
import json
import os
import pathlib
import time

ROOT = pathlib.Path("/home/z/my-project")
OUT = ROOT / "brain/lightning61_start.json"
KEY = json.loads((ROOT / "workers/secrets/lightning_tokens.json").read_text())["keys"][0]["key"]
os.environ["LIGHTNING_API_KEY"] = KEY

from lightning_sdk import Studio, Machine  # noqa: E402

ev = {"t0": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "steps": []}


def note(*a):
    line = " ".join(str(x) for x in a)
    print("[start61]", line, flush=True)
    ev["steps"].append(line)


st = Studio(name="deyoung-h3", teamspace="default-project", user="deyoungsltd")
note("status before:", str(st.status), "| machine:", str(getattr(st, "machine", "?")))

if "Stopped" in str(st.status):
    t0 = time.time()
    st.start()
    for _ in range(60):
        time.sleep(10)
        if "Running" in str(st.status):
            break
    note(f"started in {round(time.time()-t0,1)}s -> {st.status}")

# verify/ensure the T4
if st.machine is None or "T4" not in str(st.machine):
    note("machine not T4 — switching…")
    try:
        st.switch_machine(Machine.T4)
    except Exception as e:
        note("switch attempt 1 failed:", repr(e)[:120], "— retry as g4dn.xlarge")
        try:
            st.switch_machine("g4dn.xlarge")
        except Exception as e2:
            note("switch failed outright:", repr(e2)[:120])
    # machine switch restarts the studio — wait for Running again
    for _ in range(60):
        time.sleep(10)
        if "Running" in str(st.status):
            break

gpu = st.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo NO_GPU")
note("gpu probe:", gpu.strip())

# balance via REST
import requests
H = {"Authorization": f"Bearer {KEY}"}
for m in requests.get("https://lightning.ai/v1/memberships", headers=H, timeout=25).json().get("memberships", []):
    if m.get("projectId") == "01m1svndkgcbberk6v4yfcdr00":
        ev["balance_after_start"] = m.get("balance")
        note("balance:", m.get("balance"))

ev["t1"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
OUT.write_text(json.dumps(ev, indent=1))
print(json.dumps(ev, indent=1)[-400:])
