#!/usr/bin/env python3
"""Task 55: deep-probe deyoung-h3 studio for the Lightning render wiring.

Proves/disproves, with raw evidence:
  1. GPU visible inside a resumed studio (nvidia-smi, /proc/driver/nvidia, torch.cuda)
  2. What the 108G stack contains (ComfyUI? MiniMax-H3 weights? venv?)
  3. Python env that can run ComfyUI (torch build, flash-attn, etc.)
  4. Credit burn rate over the probe window

All secrets env-passed; evidence JSON -> brain/lightning55_*.json

  LIGHTNING_API_KEY=... python3 scripts/lightning_deep_probe_55.py
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
EVID = "brain/lightning55_evidence.json"


def balance():
    r = requests.get(f"{BASE}/v1/memberships",
                     headers={"Authorization": f"Bearer {KEY}"}, timeout=25)
    for m in r.json().get("memberships", []):
        if m.get("projectId") == PROJECT_ID:
            return m.get("balance")
    return None


CHECKS = r"""
set -x
echo "== GPU ==";
(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || cat /proc/driver/nvidia/version || echo NO_NVIDIA_DRIVER)
ls -la /usr/local/ | grep -i cuda || echo no_cuda_in_usr_local
echo "== PYTHON ==";
which python python3 2>/dev/null; python3 -V 2>&1
python3 - <<'PYEOF' 2>&1 | tail -5
try:
    import torch
    print("torch", torch.__version__, "cuda_available", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("gpu", torch.cuda.get_device_name(0), "vram_gb", round(torch.cuda.get_device_properties(0).total_memory/1e9, 1))
except Exception as e:
    print("torch_check_failed", repr(e))
PYEOF
echo "== STACK LAYOUT ==";
ls -la /teamspace/studios/this_studio | head -25
echo "== h3work ==";
ls /teamspace/studios/this_studio/h3work 2>/dev/null | head -25 || echo no_h3work
du -sh /teamspace/studios/this_studio/h3work 2>/dev/null
echo "== find ComfyUI ==";
ls -d /teamspace/studios/this_studio/*/ComfyUI /teamspace/studios/this_studio/ComfyUI 2>/dev/null || true
find /teamspace/studios/this_studio -maxdepth 4 -name "main.py" -path "*Comfy*" 2>/dev/null | head -5
echo "== find model weights ==";
find /teamspace/studios/this_studio -maxdepth 6 -name "*.safetensors" 2>/dev/null | head -20
echo "== find gguf/env ==";
find /teamspace/studios/this_studio -maxdepth 3 -name "*.gguf" -o -maxdepth 3 -name "environment.yml" -o -maxdepth 3 -name "requirements.txt" 2>/dev/null | head -10
echo "== venv/conda ==";
ls -d /teamspace/studios/this_studio/venv /teamspace/studios/this_studio/.venv /teamspace/studios/this_studio/miniconda* /teamspace/studios/this_studio/*env* 2>/dev/null || echo none
echo "== main.py head ==";
head -40 /teamspace/studios/this_studio/main.py 2>/dev/null || echo no_main_py
"""


def main():
    ev = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    b0 = balance()
    ev["balance_before"] = b0
    print(f"balance before: {b0}")

    st = Studio(name=STUDIO_NAME, teamspace=TEAMSPACE, user=USER)
    print("studio:", st.name, "status:", st.status)
    ev["status_before"] = str(st.status)

    t0 = time.time()
    st.start()
    ev["start_seconds"] = round(time.time() - t0, 1)
    ev["status_after_start"] = str(st.status)
    print(f"started in {ev['start_seconds']}s -> {st.status}")

    print("running deep checks (this can take a couple of minutes)...")
    t1 = time.time()
    out = st.run(CHECKS)
    ev["check_seconds"] = round(time.time() - t1, 1)
    ev["raw_output"] = out
    print(out)

    st.stop()
    time.sleep(5)
    ev["status_after_stop"] = str(st.status)
    b1 = balance()
    ev["balance_after"] = b1
    ev["burn_delta"] = None if (b0 is None or b1 is None) else round(b1 - b0, 4)
    ev["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"balance after: {b1} (delta={ev['burn_delta']})")

    os.makedirs("brain", exist_ok=True)
    with open(EVID, "w") as f:
        json.dump(ev, f, indent=1)
    print("evidence ->", EVID)


if __name__ == "__main__":
    main()
