#!/usr/bin/env python3
"""Task 55b: find out WHY deyoung-h3 resumed without a GPU and how to get one.

Steps (all evidence -> brain/lightning55b_evidence.json):
  1. REST: GET /v1/projects/{id}/cloudspaces -> machine field, gpu info, status
  2. SDK introspection: what does Studio expose for machine/switching?
  3. Inside studio: ls /dev/nvidia*, lspci | grep -i nvidia, uefi checks
  4. Attempt st.switch_machine("g4dn.2xlarge") if available, restart, re-check GPU
  5. If still no GPU: try creating a NEW studio with machine='g4dn.2xlarge'
     (name deyoung-h3b) and check GPU there. Leave STOPPED either way.

  LIGHTNING_API_KEY=... python3 scripts/lightning_gpu_fix_55b.py
"""
import json
import os
import sys
import time

KEY = os.environ.get("LIGHTNING_API_KEY", "")
if not KEY:
    print("FATAL: export LIGHTNING_API_KEY first")
    sys.exit(2)

import requests
from lightning_sdk import Studio

STUDIO_NAME = "deyoung-h3"
TEAMSPACE = "default-project"
USER = "deyoungsltd"
BASE = "https://lightning.ai"
PROJECT_ID = "01m1svndkgcbberk6v4yfcdr00"
HDR = {"Authorization": f"Bearer {KEY}"}
EVID = "brain/lightning55b_evidence.json"
ev = {}


def cloudspaces():
    r = requests.get(f"{BASE}/v1/projects/{PROJECT_ID}/cloudspaces", headers=HDR, timeout=30)
    ev["cloudspaces_http"] = r.status_code
    try:
        items = r.json().get("cloudspaces", r.json())
        out = []
        for cs in items:
            out.append({k: cs.get(k) for k in (
                "name", "status", "machine", "machineType", "gpu", "plugins",
                "artifactRestricted", "desiredState", "id") if k in cs})
        ev["cloudspaces"] = out
        return out
    except Exception as e:
        ev["cloudspaces_err"] = repr(e)
        return []


GPU_CHECK = (
    "ls /dev/nvidia* 2>&1; "
    "lspci 2>/dev/null | grep -i nvidia || echo no_lspci_nvidia; "
    "ls /usr/local/nvidia/bin 2>&1 | head -3; "
    "python3 -c \"import torch;print('torch_cuda',torch.cuda.is_available())\" 2>&1"
)


def gpu_inside(st):
    try:
        return st.run(GPU_CHECK)
    except Exception as e:
        return f"RUN_ERR {e!r}"


def main():
    cs = cloudspaces()
    for c in cs:
        print("cloudspace:", json.dumps(c)[:300])

    st = Studio(name=STUDIO_NAME, teamspace=TEAMSPACE, user=USER)
    sdk_methods = [m for m in dir(st) if not m.startswith("_")]
    ev["sdk_methods"] = sdk_methods
    print("SDK methods:", sdk_methods)

    # machine attribute?
    for attr in ("machine", "_machine", "studio_machine"):
        if hasattr(st, attr):
            try:
                ev[f"sdk_{attr}"] = str(getattr(st, attr))
                print(f"sdk {attr}:", getattr(st, attr))
            except Exception as e:
                ev[f"sdk_{attr}_err"] = repr(e)

    # 1) check inside current studio (start if stopped)
    was = str(st.status)
    if "Running" not in was:
        st.start()
        time.sleep(3)
    ev["gpu_inside_before"] = gpu_inside(st)
    print("--- GPU inside BEFORE ---")
    print(ev["gpu_inside_before"])

    # 2) try switch_machine
    switched = False
    if hasattr(st, "switch_machine"):
        for name in ("g4dn.2xlarge", "g4dn.2xlarge.gpu", "gpu", "T4"):
            try:
                print("trying switch_machine:", name)
                st.switch_machine(name)
                ev["switch_machine"] = name
                switched = True
                break
            except Exception as e:
                ev[f"switch_machine_err_{name}"] = repr(e)[:300]
                print("  err:", repr(e)[:200])
    if switched:
        try:
            st.stop()
        except Exception:
            pass
        time.sleep(5)
        st.start()
        time.sleep(10)
        ev["gpu_inside_after_switch"] = gpu_inside(st)
        print("--- GPU inside AFTER SWITCH ---")
        print(ev["gpu_inside_after_switch"])

    # 3) new studio with GPU machine
    try:
        from lightning_sdk import Studio as S
        b = S(name="deyoung-h3b", teamspace=TEAMSPACE, user=USER, machine="g4dn.2xlarge")
        ev["newstudio_created"] = True
        print("new studio deyoung-h3b resolved; starting...")
        b.start()
        time.sleep(10)
        ev["newstudio_status"] = str(b.status)
        ev["newstudio_gpu"] = gpu_inside(b)
        print("--- NEW STUDIO GPU ---")
        print(ev["newstudio_gpu"])
        b.stop()
        print("new studio stopped (kept for use, stopped to save credits)")
    except Exception as e:
        ev["newstudio_err"] = repr(e)[:500]
        print("new studio err:", repr(e)[:300])

    # always leave the original stopped unless new studio works and holds the role
    try:
        if "Running" in str(st.status):
            st.stop()
            print("original studio stopped")
    except Exception:
        pass

    ev["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(EVID, "w") as f:
        json.dump(ev, f, indent=1)
    print("evidence ->", EVID)


if __name__ == "__main__":
    main()
