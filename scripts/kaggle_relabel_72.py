#!/usr/bin/env python3
"""Task 72 — re-derive the TRUE owner of every KGAT via the CLI (env auth),
rewrite kaggle_tokens.json labels in place, and back the corrected mapping
into brain state. Never prints token values.

Bug being fixed: account labels in the vault were scrambled (e.g. the token
labeled 'youngwilly' really belongs to bittrexminingltd) -> the brain pushed
workers under the wrong identities -> SaveKernel 409s got mislabeled as
'quota blocked' and the fleet sat idle despite refilled quota.
"""
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEC = ROOT / "workers/secrets/kaggle_tokens.json"
local_bin = os.path.expanduser("~/.local/bin")
os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

data = json.load(open(SEC))
out = {}
for t in data["tokens"]:
    tid = t["id"]
    env = {**os.environ, "KAGGLE_API_TOKEN": t["token"]}
    r = subprocess.run(["kaggle", "kernels", "list", "--mine", "--page-size", "3"],
                       capture_output=True, text=True, timeout=90, env=env)
    true_user = None
    for line in r.stdout.splitlines():
        parts = [p.strip() for p in line.split()]
        if len(parts) >= 3 and "/" in parts[0] and parts[0] != "ref":
            true_user = parts[0].split("/")[0]
            break
    old = t.get("account")
    if true_user:
        t["account"] = true_user
        t["label_note"] = f"owner verified via CLI kernels/list {time.strftime('%Y-%m-%d')} (Task 72 relabel)"
    out[tid] = (old, true_user or "UNKNOWN")
    print(f"{tid}: labeled={old} -> verified={true_user or 'UNKNOWN (list failed: ' + (r.stderr or '').strip()[:60] + ')'}")

# uniqueness sanity
accs = [t.get("account") for t in data["tokens"]]
print("distinct accounts:", sorted(set(a for a in accs if a)))
json.dump(data, open(SEC, "w"), indent=2)
print("vault labels rewritten in place")
