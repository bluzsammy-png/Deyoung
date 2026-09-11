#!/usr/bin/env python3
"""Task 68 diag — WHY does the Kaggle vault round-trip mismatch 3 files?
Downloads the private dataset, hash-compares per file, and for mismatching
JSONs prints ONLY the differing KEY PATHS (values never printed).
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

OWNER, SLUG = "deyoungsltd", "deyoung-worker-vault"
REF = f"{OWNER}/{SLUG}"
VDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets"))
local_bin = os.path.expanduser("~/.local/bin")
os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")


def shape_paths(v, prefix=""):
    """Flatten JSON to {keypath: type/len signature} — no values."""
    out = {}
    if isinstance(v, dict):
        for k, x in v.items():
            out.update(shape_paths(x, f"{prefix}.{k}"))
    elif isinstance(v, list):
        out[prefix + "[]len"] = len(v)
        for i, x in enumerate(v[:4]):
            out.update(shape_paths(x, f"{prefix}[{i}]"))
    elif isinstance(v, str):
        out[prefix] = f"str:{len(v)}"
    else:
        out[prefix] = type(v).__name__
    return out


with tempfile.TemporaryDirectory() as dl:
    r = subprocess.run(["kaggle", "datasets", "download", REF, "-p", dl, "--unzip"],
                       capture_output=True, text=True, timeout=300)
    remote_files = sorted(os.listdir(dl))
    print("remote dataset files:", remote_files)
    local_files = sorted(f for f in os.listdir(VDIR) if f.endswith(".json") and not f.startswith("."))
    print("local secret files: ", local_files)
    for name in sorted(set(remote_files) | set(local_files)):
        if not name.endswith(".json"):
            continue
        lp = os.path.join(VDIR, name)
        rp = os.path.join(dl, name)
        if not (os.path.exists(lp) and os.path.exists(rp)):
            print(f"  {name}: PRESENT local={os.path.exists(lp)} remote={os.path.exists(rp)}")
            continue
        lb = open(lp, "rb").read()
        rb = open(rp, "rb").read()
        same = hashlib.sha256(lb).hexdigest() == hashlib.sha256(rb).hexdigest()
        print(f"  {name}: {'MATCH' if same else 'DIFF'} (local {len(lb)}B / remote {len(rb)}B)")
        if not same and name.endswith(".json"):
            try:
                lsig = shape_paths(json.loads(lb))
                rsig = shape_paths(json.loads(rb))
                only_l = {k: v for k, v in lsig.items() if rsig.get(k) != v}
                only_r = {k: v for k, v in rsig.items() if lsig.get(k) != v}
                if only_l:
                    print(f"    local-only sig: {only_l}")
                if only_r:
                    print(f"    remote-only sig: {only_r}")
            except Exception as e:
                print(f"    (json sig failed: {type(e).__name__})")
