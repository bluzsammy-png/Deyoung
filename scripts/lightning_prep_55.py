#!/usr/bin/env python3
"""Task 55: foreground studio prep — bring deyoung-h3 up on the T4 machine.

Designed to run FOREGROUND under the bash tool timeout: every step prints and
writes evidence immediately. Does NOT push the worker (controller does that).

  python3 scripts/lightning_prep_55.py
"""
import json
import os
import pathlib
import time

ROOT = pathlib.Path("/home/z/my-project")
KEY = json.loads((ROOT / "workers/secrets/lightning_tokens.json").read_text())["keys"][0]["key"]
os.environ["LIGHTNING_API_KEY"] = KEY
EVID = ROOT / "brain/lightning_prep55_evidence.json"


def ev(update=None, **kw):
    if update:
        kw.update(update)
    d = {}
    if EVID.exists():
        try:
            d = json.loads(EVID.read_text())
        except Exception:
            pass
    d.update(kw)
    d["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    EVID.write_text(json.dumps(d, indent=1))


from lightning_sdk import Studio  # noqa: E402
from lightning_sdk.machine import Machine  # noqa: E402

st = Studio(name="deyoung-h3", teamspace="default-project", user="deyoungsltd")
print("status:", st.status, "machine:", getattr(st, "machine", "?"), flush=True)
ev({"status": str(st.status)})

# settle to Running (start if Stopped)
for i in range(30):
    s = str(st.status)
    if "Running" in s:
        break
    if "Stopped" in s:
        t0 = time.time()
        st.start()
        print(f"started in {time.time()-t0:.0f}s", flush=True)
        ev(start_seconds=round(time.time() - t0, 1))
        break
    print("waiting:", s, flush=True)
    time.sleep(12)
    if i == 29:
        raise SystemExit("studio never settled")

time.sleep(10)
machine = str(getattr(st, "machine", "?"))
print("machine now:", machine, flush=True)

if "T4" not in machine:
    print("switching to T4 (blocks ~1-4 min)...", flush=True)
    st.switch_machine(Machine.T4)
    ev({"switch": "T4 requested", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    print("switch_machine returned", flush=True)
    for i in range(50):
        s = str(st.status)
        if "Running" in s:
            break
        time.sleep(12)
    machine = str(getattr(st, "machine", "?"))
    print("machine after switch:", machine, flush=True)

# GPU verify
gpu = ""
for i in range(20):
    gpu = st.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | head -1").strip()
    if "Tesla" in gpu or "T4" in gpu:
        break
    print("gpu not ready:", gpu[:60], flush=True)
    time.sleep(15)

ev({"machine": machine, "gpu": gpu})
print("FINAL:", str(st.status), machine, "|", gpu, flush=True)
if "Tesla" not in gpu and "T4" not in gpu:
    raise SystemExit("GPU never came up")
print("PREP OK - studio Running on T4 with GPU verified", flush=True)
