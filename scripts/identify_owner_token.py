#!/usr/bin/env python3
"""Identify which vault token owns deyoungsltd by attempting to download the
private offsite vault dataset. First success = owner token; its download IS
the backup recovery. Never prints token values."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "kaggle_tokens.json"))
REF = "deyoungsltd/deyoung-worker-vault"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets"))
TOK_PATH = os.path.expanduser("~/.kaggle/access_token")

local_bin = os.path.expanduser("~/.local/bin")
os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

def try_download(tok: str, dest: str) -> tuple[bool, str]:
    with open(TOK_PATH, "w") as f:
        f.write(tok + "\n")
    os.chmod(TOK_PATH, 0o600)
    r = subprocess.run(
        ["kaggle", "datasets", "download", REF, "-p", dest, "--unzip"],
        capture_output=True, text=True, timeout=120,
    )
    out = (r.stdout + r.stderr).lower()
    ok = r.returncode == 0 and ("download" in out or "unzip" in out or os.path.isdir(dest) and os.listdir(dest))
    return ok, (r.stdout + r.stderr)[:200]

def main():
    data = json.load(open(VAULT))
    found = None
    for i, t in enumerate(data["tokens"], 1):
        tmp = tempfile.mkdtemp(prefix="vaultrec_")
        try:
            ok, msg = try_download(t["token"], tmp)
            files = os.listdir(tmp) if os.path.isdir(tmp) else []
            print(f"token {i}: {'OWNER — download OK' if ok else 'foreign/blocked'} ({len(files)} files)")
            if ok and files:
                found = (i, tmp)
                break
        except Exception as e:
            print(f"token {i}: error {type(e).__name__}: {str(e)[:120]}")
        finally:
            if not (found and found[1] == tmp):
                shutil.rmtree(tmp, ignore_errors=True)
    if not found:
        print("RESULT: no token could read the offsite dataset")
        sys.exit(1)
    i, tmp = found
    # copy recovered files next to the vault (staging dir), don't overwrite new vault files blindly
    stage = os.path.join(OUT, "_recovered")
    os.makedirs(stage, exist_ok=True)
    for f in os.listdir(tmp):
        shutil.copy2(os.path.join(tmp, f), os.path.join(stage, f))
    shutil.rmtree(tmp, ignore_errors=True)
    data["tokens"][i - 1]["account"] = "deyoungsltd"
    json.dump(data, open(VAULT, "w"), indent=2)
    os.chmod(VAULT, 0o600)
    print(f"RESULT: token #{i} = deyoungsltd (owner). Recovered files staged in workers/secrets/_recovered/: {sorted(os.listdir(stage))}")

main()
