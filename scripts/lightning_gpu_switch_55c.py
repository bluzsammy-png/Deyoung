#!/usr/bin/env python3
"""Task 55c: incrementally switch deyoung-h3 onto a real GPU machine.

Writes brain/lightning55c_evidence.json after EVERY step so timeouts lose nothing.

  LIGHTNING_API_KEY=... python3 scripts/lightning_gpu_switch_55c.py
"""
import json
import os
import sys
import time

KEY = os.environ.get("LIGHTNING_API_KEY", "")
if not KEY:
    print("FATAL: export LIGHTNING_API_KEY first")
    sys.exit(2)

from lightning_sdk import Studio
from lightning_sdk.machine import Machine

EVID = "brain/lightning55c_evidence.json"
ev = {"t0": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def save():
    with open(EVID, "w") as f:
        json.dump(ev, f, indent=1)


def saveprint(*a):
    print(*a, flush=True)
    save()


GPU_CHECK = (
    "ls /dev/nvidia* 2>&1 | head -4; "
    "python3 -c \"import torch;print('torch_cuda',torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')\" 2>&1"
)


def main():
    st = Studio(name="deyoung-h3", teamspace="default-project", user="deyoungsltd")
    saveprint("studio resolved")

    # step 1: START first (SDK requires running studio to switch machines)
    for _ in range(30):
        s = str(st.status)
        if "Running" in s:
            break
        if "Stopped" in s:
            t0 = time.time()
            st.start()
            saveprint(f"started in {round(time.time()-t0,1)}s -> {st.status}")
            break
        saveprint(f"status {s} - waiting for it to settle...")
        time.sleep(10)
    saveprint("status:", str(st.status))

    # step 2: switch machine
    try:
        saveprint("switching to Machine.T4 ...")
        st.switch_machine(Machine.T4)
        ev["switch"] = "Machine.T4 accepted"
        saveprint("switch accepted")
    except Exception as e:
        ev["switch_err"] = repr(e)[:400]
        saveprint("switch err:", repr(e)[:300])
        # try string form
        try:
            saveprint("retrying with string 'g4dn.xlarge'...")
            st.switch_machine("g4dn.xlarge")
            ev["switch2"] = "string accepted"
        except Exception as e2:
            ev["switch2_err"] = repr(e2)[:400]
            saveprint("switch2 err:", repr(e2)[:300])
            return

    saveprint("machine now:", str(getattr(st, "machine", "?")))

    # step 3: give the restart a beat, then GPU check (studio stays up through switch)
    try:
        time.sleep(20)
        ev["gpu"] = st.run(GPU_CHECK)
        saveprint("--- GPU CHECK ---")
        saveprint(ev["gpu"])
    except Exception as e:
        ev["gpu_err"] = repr(e)[:500]
        saveprint("gpu check err:", repr(e)[:300])

    # step 4: leave STOPPED (credit guard) - wiring comes next
    try:
        st.stop()
        ev["final_status"] = str(st.status)
        saveprint("studio stopped (credit guard until worker wired)")
    except Exception as e:
        ev["stop_err"] = repr(e)[:200]
        saveprint("stop err:", repr(e)[:200])

    ev["done_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save()


if __name__ == "__main__":
    main()
