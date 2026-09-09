#!/usr/bin/env python3
"""Task 54: prove headless control of the owner's deyoung-h3 Lightning Studio.

Starts the studio, runs nvidia-smi + a filesystem peek inside it, stops it,
and reports the credit balance delta. Non-destructive: read-only commands.

  LIGHTNING_API_KEY=... LIGHTNING_USER_ID=... python3 scripts/lightning_studio_probe_54.py
"""
import json
import os
import sys
import time

KEY = os.environ.get("LIGHTNING_API_KEY", "")
UID = os.environ.get("LIGHTNING_USER_ID", "")
if not KEY or not UID:
    print("FATAL: export LIGHTNING_API_KEY and LIGHTNING_USER_ID first")
    sys.exit(2)

import requests
from lightning_sdk import Studio

STUDIO_NAME = "deyoung-h3"
TEAMSPACE = "default-project"
USER = "deyoungsltd"
BASE = "https://lightning.ai"
PROJECT_ID = "01m1svndkgcbberk6v4yfcdr00"


def balance():
    r = requests.get(f"{BASE}/v1/memberships",
                     headers={"Authorization": f"Bearer {KEY}"}, timeout=25)
    for m in r.json().get("memberships", []):
        if m.get("projectId") == PROJECT_ID:
            return m.get("balance")
    return None


def main():
    b0 = balance()
    print(f"balance before: {b0}")

    st = Studio(name=STUDIO_NAME, teamspace=TEAMSPACE, user=USER)
    print("studio resolved:", st.name, "| status:", st.status)

    print("starting studio (T4 g4dn.2xlarge resume) ...")
    t0 = time.time()
    st.start()
    print(f"start() returned after {time.time()-t0:.0f}s; status: {st.status}")

    print("--- nvidia-smi inside studio ---")
    out = st.run("nvidia-smi --query-gpu=name,memory.total,driver_version "
                 "--format=csv,noheader")
    print(out)

    print("--- stack peek inside studio ---")
    out2 = st.run(
        "ls -dt /teamspace/studios/* 2>/dev/null | head -3; "
        "du -sh /teamspace/studios/this_studio 2>/dev/null | tail -1; "
        "ls /teamspace/studios/this_studio 2>/dev/null | head -15")
    print(out2)

    print("stopping studio ...")
    st.stop()
    time.sleep(5)
    print("status after stop:", st.status)

    b1 = balance()
    print(f"balance after: {b1} (delta={None if (b0 is None or b1 is None) else round(b1-b0, 4)})")
    print("HEADLESS CONTROL: PROVEN" if out else "HEADLESS CONTROL: NO OUTPUT")


if __name__ == "__main__":
    main()
