#!/usr/bin/env python3
"""Task 68 — poll the private Kaggle vault backup until the pushed version
finels processing and hash-matches local workers/secrets/*.json.
Polls every 60s (max 10 tries). Prints file names + MATCH/DIFF only.
"""
import hashlib
import os
import subprocess
import tempfile
import time

REF = "deyoungsltd/deyoung-worker-vault"
VDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets"))
local_bin = os.path.expanduser("~/.local/bin")
os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

local = {f: open(os.path.join(VDIR, f), "rb").read()
         for f in sorted(os.listdir(VDIR))
         if f.endswith(".json") and not f.startswith(".")}
print(f"local files: {len(local)} -> {list(local)}")

for attempt in range(1, 11):
    with tempfile.TemporaryDirectory() as dl:
        r = subprocess.run(["kaggle", "datasets", "download", REF, "-p", dl, "--unzip"],
                           capture_output=True, text=True, timeout=300)
        remote = {}
        for f in os.listdir(dl):
            if f.endswith(".json"):
                remote[f] = open(os.path.join(dl, f), "rb").read()
    if not remote:
        print(f"[{attempt}/10] download empty ({(r.stderr or '').strip()[:80]}) — processing, retry 60s")
    else:
        missing = sorted(set(local) - set(remote))
        diff = sorted(f for f in local if f in remote
                      and hashlib.sha256(local[f]).hexdigest() != hashlib.sha256(remote[f]).hexdigest())
        extra = sorted(set(remote) - set(local))
        print(f"[{attempt}/10] remote {len(remote)} files | missing={missing} diff={diff} extra={extra}")
        if not missing and not diff and not extra:
            print("VAULT BACKUP ROUND-TRIP: PASS (all files hash-identical, private dataset)")
            raise SystemExit(0)
    time.sleep(60)
print("VAULT BACKUP ROUND-TRIP: FAIL after 10 polls")
raise SystemExit(1)
